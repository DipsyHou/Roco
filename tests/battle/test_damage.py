from __future__ import annotations

from unittest.mock import patch

import pytest

from roco.core.battle.utils import apply_damage, apply_heal, calculate_damage, make_effect
from roco.core.battle.types import DamageType, EffectType, StatType


def test_apply_damage_and_heal_clamp_hp_but_report_overflow(standard_engine):
    spirit = standard_engine.get_all_spirits("p1")[0]
    spirit.current_hp = 100

    assert apply_damage(spirit, 150) == 150
    assert spirit.current_hp == 0
    assert not spirit.is_alive

    spirit.is_alive = True
    spirit.current_hp = spirit.max_hp
    assert apply_heal(spirit, 99999) == 99999
    assert spirit.current_hp == spirit.max_hp


@pytest.mark.parametrize(
    ("raw", "damage_type", "defense", "expected"),
    [
        (200, DamageType.physical, 200, 100),
        (200, DamageType.magical, 200, 100),
        (100, DamageType.fixed, 0, 100),
    ],
)
def test_damage_types_use_expected_defense(raw, damage_type, defense, expected, standard_engine):
    attacker = standard_engine.get_all_spirits("p1")[0]
    defender = standard_engine.get_all_spirits("p2")[0]
    defender.base_stats.def_ = defense
    defender.base_stats.mag_def = defense

    assert calculate_damage(raw, damage_type, attacker, defender) == expected


def test_damage_pipeline_combines_percent_flat_reduction_and_cap(standard_engine):
    attacker = standard_engine.get_all_spirits("p1")[0]
    defender = standard_engine.get_all_spirits("p2")[0]
    defender.base_stats.def_ = 100
    attacker.effects.extend(
        [
            make_effect(EffectType.buff_damage_percent_boost, "a", duration_turns=1, damage_type=DamageType.physical, value=0.2),
            make_effect(EffectType.buff_damage_flat_boost, "a", duration_turns=1, value=20),
        ]
    )
    defender.effects.extend(
        [
            make_effect(EffectType.buff_taken_damage_percent_reduction, "d", duration_turns=1, damage_type=DamageType.physical, value=0.3),
            make_effect(EffectType.buff_taken_damage_flat_reduction, "d", duration_turns=1, value=10),
            make_effect(EffectType.buff_damage_cap, "d", duration_turns=1, value=200),
        ]
    )

    assert calculate_damage(200, DamageType.physical, attacker, defender) == 172


def test_taken_damage_percent_reduction_persists_across_hits(standard_engine):
    attacker = standard_engine.get_all_spirits("p1")[0]
    defender = standard_engine.get_all_spirits("p2")[0]
    defender.base_stats.def_ = 100
    defender.effects.append(
        make_effect(
            EffectType.buff_taken_damage_percent_reduction,
            "f",
            duration_turns=2,
            value=0.20,
        )
    )

    assert calculate_damage(200, DamageType.physical, attacker, defender) == 160
    assert len(defender.effects) == 1
    assert calculate_damage(200, DamageType.physical, attacker, defender) == 160
    assert len(defender.effects) == 1


def test_crit_applies_to_base_before_damage_modifiers(standard_engine):
    attacker = standard_engine.get_all_spirits("p1")[0]
    defender = standard_engine.get_all_spirits("p2")[0]
    defender.base_stats.def_ = 200
    attacker.effects.extend(
        [
            make_effect(EffectType.buff_crit_rate, "a", duration_turns=1, value=1.0),
            make_effect(EffectType.buff_crit_damage, "a", duration_turns=1, value=100),
        ]
    )

    with patch("roco.core.battle.damage.random.random", return_value=0.0):
        crit = calculate_damage(200, DamageType.physical, attacker, defender)

    assert crit == 200


def test_crit_default_is_no_bonus_without_buffs(standard_engine):
    attacker = standard_engine.get_all_spirits("p1")[0]
    defender = standard_engine.get_all_spirits("p2")[0]
    defender.base_stats.def_ = 200

    with patch("roco.core.battle.damage.random.random", return_value=0.0):
        assert calculate_damage(200, DamageType.physical, attacker, defender) == 100


def test_crit_rate_zero_skips_roll(standard_engine):
    """Most damage has 0% crit rate; pipeline still runs but never multiplies."""
    attacker = standard_engine.get_all_spirits("p1")[0]
    defender = standard_engine.get_all_spirits("p2")[0]
    defender.base_stats.def_ = 200
    attacker.effects.append(
        make_effect(EffectType.buff_crit_damage, "a", duration_turns=1, value=100)
    )

    with patch("roco.core.battle.damage.random.random", return_value=0.0) as roll:
        assert calculate_damage(200, DamageType.physical, attacker, defender) == 100
    roll.assert_not_called()


def test_effective_stat_modifiers_still_work_after_field_split(standard_engine):
    from roco.core.battle.utils import get_effective_stat

    spirit = standard_engine.get_all_spirits("p1")[0]
    spirit.base_stats.atk = 200
    spirit.effects.extend(
        [
            make_effect(EffectType.buff_stat_percent_boost, "src", duration_turns=1, stat_type=StatType.atk, value=0.2),
            make_effect(EffectType.buff_stat_flat_boost, "src", duration_turns=1, stat_type=StatType.atk, value=30),
        ]
    )

    assert get_effective_stat(spirit, StatType.atk) == 270


def test_critical_log_is_generated_by_shared_combat_helper(standard_engine):
    from roco.core.spirits._combat import deal_damage

    attacker = standard_engine.get_all_spirits("p1")[0]
    defender = standard_engine.get_all_spirits("p2")[0]
    attacker.effects.append(
        make_effect(EffectType.buff_crit_rate, "a", duration_turns=1, value=1.0)
    )

    start = len(standard_engine.state.battle_log)
    deal_damage(
        standard_engine,
        attacker,
        defender,
        100,
        DamageType.fixed,
        lambda actual: f"测试伤害 {actual}",
    )

    new_logs = standard_engine.state.battle_log[start:]
    crit_logs = [log for log in new_logs if log.data and log.data.get("critical")]
    assert len(crit_logs) == 1
    assert crit_logs[0].message.startswith("暴击！")
    assert new_logs.index(crit_logs[0]) < next(
        i for i, log in enumerate(new_logs) if log.message.startswith("测试伤害")
    )


def test_critical_log_is_generated_for_default_normal_attack(standard_engine):
    attacker = standard_engine.get_all_spirits("p1")[0]
    defender = standard_engine.get_all_spirits("p2")[0]
    attacker.effects.append(
        make_effect(EffectType.buff_crit_rate, "a", duration_turns=1, value=1.0)
    )

    start = len(standard_engine.state.battle_log)
    standard_engine.execute_action(
        attacker.owner_id,
        {
            "type": "normal_attack",
            "actorId": attacker.unique_id,
            "targetId": defender.unique_id,
        },
    )

    new_logs = standard_engine.state.battle_log[start:]
    assert sum(1 for log in new_logs if log.data and log.data.get("critical")) == 1
