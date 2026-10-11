from __future__ import annotations

from roco.core.battle.damage_modifiers import SUSTAINED_DAMAGE_TAG
from roco.core.battle.dot import process_poison_damage
from roco.core.battle.utils import apply_burn_stacks, apply_poison_stacks, calculate_damage, make_effect
from roco.core.battle.types import DamageType, EffectType
from tests.conftest import by_template, P1


def test_burn_applies_general_percent_boost(standard_engine):
    """Burn is fire attribute damage and receives generic attribute boosts."""
    attacker = standard_engine.get_all_spirits("p1")[0]
    defender = standard_engine.get_all_spirits("p2")[0]
    defender.base_stats.defense = 100
    defender.elements = ()
    attacker.base_stats.attack = 200
    attacker.effects.append(
        make_effect(
            EffectType.buff_damage_percent_boost,
            attacker.unique_id,
            duration_turns=1,
            value=0.5,
        )
    )
    apply_burn_stacks(defender, attacker.unique_id, 1)

    plain = calculate_damage(20, DamageType.fire, attacker, defender, sustained="burn")
    boosted = calculate_damage(20, DamageType.fire, attacker, defender)
    assert plain == 30
    assert boosted == 30


def test_burn_applies_sustained_taken_amp(standard_engine):
    attacker = standard_engine.get_all_spirits("p1")[0]
    defender = standard_engine.get_all_spirits("p2")[0]
    defender.base_stats.defense = 100
    defender.elements = ()
    attacker.base_stats.attack = 200
    defender.effects.append(
        make_effect(
            EffectType.debuff_taken_damage_percent_boost,
            attacker.unique_id,
            duration_turns=3,
            value=0.15,
            display_name="毛血旺",
            effect_tag=SUSTAINED_DAMAGE_TAG,
        )
    )

    base = calculate_damage(20, DamageType.fire, attacker, defender, sustained="burn")
    assert base == 23


def test_burn_applies_general_taken_amp(standard_engine):
    attacker = standard_engine.get_all_spirits("p1")[0]
    defender = standard_engine.get_all_spirits("p2")[0]
    defender.base_stats.defense = 100
    defender.elements = ()
    defender.effects.append(
        make_effect(
            EffectType.debuff_taken_damage_percent_boost,
            attacker.unique_id,
            duration_turns=3,
            value=0.16,
        )
    )
    assert calculate_damage(20, DamageType.fire, attacker, defender, sustained="burn") == 23


def test_poison_uses_attribute_and_sustained_modifiers(standard_engine):
    defender = standard_engine.get_all_spirits("p2")[0]
    source = standard_engine.get_all_spirits("p1")[0]
    defender.max_hp = 1000
    defender.current_hp = 1000
    defender.base_stats.defense = 100
    defender.elements = ()
    defender.effects.extend(
        [
            make_effect(
                EffectType.debuff_taken_damage_percent_boost,
                "src",
                duration_turns=3,
                value=0.15,
                display_name="毛血旺",
                effect_tag=SUSTAINED_DAMAGE_TAG,
            ),
            make_effect(
                EffectType.buff_taken_damage_percent_reduction,
                "src",
                duration_turns=3,
                value=0.5,
            ),
        ]
    )
    apply_poison_stacks(defender, source.unique_id, 10)

    process_poison_damage(standard_engine, defender, decrease=False)
    assert defender.current_hp == 935


def test_poison_ignores_fixed_taken_amp(standard_engine):
    defender = standard_engine.get_all_spirits("p2")[0]
    source = standard_engine.get_all_spirits("p1")[0]
    defender.max_hp = 1000
    defender.current_hp = 1000
    defender.base_stats.defense = 100
    defender.elements = ()
    defender.effects.append(
        make_effect(
            EffectType.debuff_taken_damage_percent_boost,
            "src",
            duration_turns=3,
            damage_type=DamageType.fixed,
            value=0.5,
        )
    )
    apply_poison_stacks(defender, source.unique_id, 10)
    process_poison_damage(standard_engine, defender, decrease=False)
    assert defender.current_hp == 900


def test_poison_ignores_source_fixed_damage_boost(standard_engine):
    source = standard_engine.get_all_spirits("p1")[0]
    defender = standard_engine.get_all_spirits("p2")[0]
    defender.max_hp = defender.current_hp = 1000
    defender.base_stats.defense = 100
    defender.elements = ()
    source.effects.append(
        make_effect(
            EffectType.buff_damage_percent_boost,
            source.unique_id,
            duration_turns=3,
            damage_type=DamageType.fixed,
            value=0.5,
        )
    )
    apply_poison_stacks(defender, source.unique_id, 10)

    process_poison_damage(standard_engine, defender, decrease=False)

    assert defender.current_hp == 900


def test_poison_is_not_reduced_by_fixed_damage_passive(engine_factory):
    engine = engine_factory(
        ("cixiyi", "flora", "tita", "fanying", "clawdragon"),
        ("steamdragon", "chaosling", "qiuka", "starweaver", "huxian"),
    )
    cx = by_template(engine, P1, "cixiyi")
    source = by_template(engine, P1, "flora")
    cx.max_hp = 1000
    cx.current_hp = 1000
    cx.base_stats.defense = 100
    apply_poison_stacks(cx, source.unique_id, 10)

    process_poison_damage(engine, cx, decrease=False)
    assert cx.current_hp == 925  # Ground resists poison by 25%; harden skin is fixed-only.


def test_poison_is_one_percent_max_hp_per_stack(standard_engine):
    defender = standard_engine.get_all_spirits("p2")[0]
    source = standard_engine.get_all_spirits("p1")[0]
    defender.max_hp = defender.current_hp = 1234
    defender.base_stats.defense = 100
    defender.elements = ()
    apply_poison_stacks(defender, source.unique_id, 3)

    process_poison_damage(standard_engine, defender, decrease=False)

    assert defender.current_hp == 1197  # int(1234 * 1% * 3)
