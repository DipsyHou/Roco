from __future__ import annotations

from roco.core.battle.dot import process_freeze_on_action_end
from roco.core.battle.effects import (
    adjust_skill_energy_cost,
    apply_skill_energy_cost_increase,
    get_freeze_stacks,
    make_effect,
)
from roco.core.battle.types import DamageType, EffectType, StatType
from roco.core.battle.utils import calculate_damage, get_effective_stat
from roco.core.spirits import get_spirit_template
from tests.conftest import P1, P2, by_template, cast_skill, effects_of

TEAM = ("daermao", "flora", "clawdragon", "chaosling", "starweaver")


def _daermao(engine):
    return by_template(engine, P1, "daermao")


def test_qingwu_increases_all_skill_energy_cost(engine_factory):
    engine = engine_factory(TEAM)
    dm = _daermao(engine)
    enemy = engine.get_active_spirits(P2)[0]
    tpl = get_spirit_template("flora")

    assert cast_skill(engine, dm, "daermao_skill1", enemy)

    debuffs = effects_of(enemy, EffectType.debuff_skill_energy_cost_increase)
    assert len(debuffs) == 1
    assert debuffs[0].effect_tag == "*"
    assert debuffs[0].value == 1
    assert debuffs[0].duration_turns == 3

    for skill in tpl.skills:
        assert engine.effective_skill_energy_cost(enemy, skill) == (skill.energy_cost or 0) + 1


def test_energy_cost_unified_with_xiaozong_reduction(engine_factory):
    engine = engine_factory(("xiaozong", "flora", "clawdragon", "chaosling", "starweaver"))
    xz = by_template(engine, P1, "xiaozong")
    tpl = get_spirit_template("xiaozong")
    skill1 = tpl.skills[0]

    assert cast_skill(engine, xz, "xiaozong_skill3")
    assert engine.effective_skill_energy_cost(xz, skill1) == 2

    base = skill1.energy_cost or 0
    assert adjust_skill_energy_cost(xz, skill1.id, base) == 2
    assert adjust_skill_energy_cost(xz, skill1.id, base + 1) == 3


def test_qingwu_and_reduction_net_on_same_spirit(engine_factory):
    engine = engine_factory(TEAM)
    spirit = _daermao(engine)
    skill_id = "daermao_skill1"
    base = 2

    apply_skill_energy_cost_increase(spirit, "src", increase=1, duration_turns=3)
    spirit.effects.append(
        make_effect(
            EffectType.buff_skill_energy_cost_reduction,
            spirit.unique_id,
            duration_turns=2,
            value=1,
            effect_tag=skill_id,
        )
    )
    assert adjust_skill_energy_cost(spirit, skill_id, base) == base


def test_feixian_applies_freeze_stacks_to_target_and_adjacent(engine_factory):
    engine = engine_factory(TEAM)
    dm = _daermao(engine)
    enemies = engine.get_active_spirits(P2)
    target = enemies[0]
    adjacent = next(
        (e for e in enemies if e.unique_id != target.unique_id and abs(e.slot - target.slot) == 1),
        None,
    )

    assert cast_skill(engine, dm, "daermao_skill2", target)

    assert get_freeze_stacks(target) == 6
    if adjacent is not None:
        assert get_freeze_stacks(adjacent) == 3
    for enemy in enemies:
        if enemy.unique_id not in {target.unique_id, getattr(adjacent, "unique_id", None)}:
            assert get_freeze_stacks(enemy) == 0


def test_freeze_executes_when_hp_below_threshold(engine_factory):
    engine = engine_factory(TEAM)
    enemy = engine.get_active_spirits(P2)[0]
    enemy.max_hp = 600
    enemy.current_hp = 20

    enemy.effects.append(make_effect(EffectType.debuff_freeze, "src", stacks=4))

    process_freeze_on_action_end(engine, enemy)

    assert not enemy.is_alive


def test_freeze_executes_at_exact_threshold(engine_factory):
    engine = engine_factory(TEAM)
    enemy = engine.get_active_spirits(P2)[0]
    enemy.max_hp = 600
    enemy.current_hp = 24

    enemy.effects.append(make_effect(EffectType.debuff_freeze, "src", stacks=4))

    process_freeze_on_action_end(engine, enemy)

    assert not enemy.is_alive


def test_freeze_does_not_execute_above_threshold(engine_factory):
    engine = engine_factory(TEAM)
    enemy = engine.get_active_spirits(P2)[0]
    enemy.max_hp = 600
    enemy.current_hp = 25

    enemy.effects.append(make_effect(EffectType.debuff_freeze, "src", stacks=4))

    process_freeze_on_action_end(engine, enemy)

    assert enemy.is_alive


def test_chunbai_purges_buffs_on_skill(engine_factory):
    engine = engine_factory(TEAM)
    dm = _daermao(engine)
    enemy = engine.get_active_spirits(P2)[0]

    for _ in range(2):
        enemy.effects.append(
            make_effect(
                EffectType.buff_stat_percent_boost,
                enemy.unique_id,
                duration_turns=3,
                stat_type=StatType.atk,
                value=0.1,
            )
        )

    assert cast_skill(engine, dm, "daermao_skill1", enemy)

    buffs = [e for e in enemy.effects if e.type.value.startswith("buff_")]
    assert len(buffs) == 1


def test_menghua_reduces_outgoing_damage(engine_factory):
    engine = engine_factory(TEAM)
    dm = _daermao(engine)
    enemy = engine.get_active_spirits(P2)[0]
    ally = engine.get_active_spirits(P1)[1]

    assert cast_skill(engine, dm, "daermao_skill3", enemy)

    debuffs = effects_of(enemy, EffectType.debuff_damage_percent_reduction)
    assert len(debuffs) == 1
    assert debuffs[0].value == 0.33

    raw = get_effective_stat(enemy, StatType.atk)
    without = calculate_damage(raw, DamageType.physical, ally, dm)
    with_menghua = calculate_damage(raw, DamageType.physical, enemy, dm)
    assert with_menghua < without
