from __future__ import annotations

from roco.core.battle.dot import (
    process_burn_on_action_end,
    process_poison_on_action_end,
    trigger_burn_damage,
)
from roco.core.battle.effects import apply_burn_stacks, apply_poison_stacks, get_burn_effects
from roco.core.battle.types import EffectType


def test_burn_resolves_per_source_then_halves_at_action_end(standard_engine):
    source_a = standard_engine.get_all_spirits("p1")[0]
    source_b = standard_engine.get_all_spirits("p1")[1]
    target = standard_engine.get_all_spirits("p2")[0]
    apply_burn_stacks(target, source_a.unique_id, 4)
    apply_burn_stacks(target, source_b.unique_id, 2)
    hp_before = target.current_hp

    process_burn_on_action_end(standard_engine, target)

    assert target.current_hp < hp_before
    remaining = {effect.source_id: effect.stacks for effect in get_burn_effects(target)}
    assert remaining == {source_a.unique_id: 2, source_b.unique_id: 1}


def test_trigger_burn_damage_resolves_every_source_without_halving(standard_engine):
    source_a = standard_engine.get_all_spirits("p1")[0]
    source_b = standard_engine.get_all_spirits("p1")[1]
    target = standard_engine.get_all_spirits("p2")[0]
    apply_burn_stacks(target, source_a.unique_id, 4)
    apply_burn_stacks(target, source_b.unique_id, 2)
    hp_before = target.current_hp

    trigger_burn_damage(standard_engine, target)

    assert target.current_hp < hp_before
    remaining = {effect.source_id: effect.stacks for effect in get_burn_effects(target)}
    assert remaining == {source_a.unique_id: 4, source_b.unique_id: 2}


def test_burn_from_dead_source_decays_without_damage(standard_engine):
    source = standard_engine.get_all_spirits("p1")[0]
    target = standard_engine.get_all_spirits("p2")[0]
    source.is_alive = False
    apply_burn_stacks(target, source.unique_id, 3)
    hp_before = target.current_hp

    process_burn_on_action_end(standard_engine, target)

    assert target.current_hp == hp_before
    assert get_burn_effects(target)[0].stacks == 1


def test_poison_ticks_at_end_and_decays(standard_engine):
    source = standard_engine.get_all_spirits("p1")[0]
    target = standard_engine.get_all_spirits("p2")[0]
    apply_poison_stacks(target, source.unique_id, 2)
    hp_before = target.current_hp

    process_poison_on_action_end(standard_engine, target)

    poison = next(effect for effect in target.effects if effect.type == EffectType.debuff_poison)
    assert target.current_hp < hp_before
    assert poison.stacks == 1