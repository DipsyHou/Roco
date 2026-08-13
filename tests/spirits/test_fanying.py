from __future__ import annotations

from tests.conftest import P1, P2, by_template, cast_skill, effects_of
from roco.core.battle.types import EffectType


def test_tailwind_exists_from_battle_start_and_grants_speed_aura(engine_factory):
    engine = engine_factory(("fanying", "flora", "clawdragon", "chaosling", "starweaver"))
    fanying = by_template(engine, P1, "fanying")
    adjacent = by_template(engine, P1, "flora")
    far = by_template(engine, P1, "chaosling")

    assert effects_of(fanying, EffectType.state_tailwind)
    assert engine.get_effective_speed(fanying) == fanying.base_stats.speed * 1.08
    assert engine.get_effective_speed(adjacent) == adjacent.base_stats.speed * 1.04
    assert engine.get_effective_speed(far) == far.base_stats.speed


def test_wing_guard_grants_speed_and_advance_on_hit(engine_factory):
    engine = engine_factory(("fanying", "flora", "clawdragon", "chaosling", "starweaver"))
    fanying = by_template(engine, P1, "fanying")
    ally = by_template(engine, P1, "clawdragon")
    assert cast_skill(engine, fanying, "fanying_skill2", ally)

    assert engine.get_effective_speed(ally) == ally.base_stats.speed * 1.08

    charge_before = ally.charge
    engine.notify_damage_taken(fanying, ally, 10)
    assert ally.charge < charge_before


def test_wing_guard_moves_to_selected_ally(engine_factory):
    engine = engine_factory(("fanying", "flora", "clawdragon", "chaosling", "starweaver"))
    fanying = by_template(engine, P1, "fanying")
    first = by_template(engine, P1, "flora")
    second = by_template(engine, P1, "clawdragon")

    assert cast_skill(engine, fanying, "fanying_skill2", first)
    assert effects_of(first, EffectType.state_wing_guard)
    assert cast_skill(engine, fanying, "fanying_skill2", second)

    assert not effects_of(first, EffectType.state_wing_guard)
    assert effects_of(second, EffectType.state_wing_guard)


def test_your_turn_buffs_allies_and_stuns_enemies(engine_factory):
    engine = engine_factory(("fanying", "flora", "clawdragon", "chaosling", "starweaver"))
    fanying = by_template(engine, P1, "fanying")
    ally = by_template(engine, P1, "flora")
    enemy = engine.get_active_spirits(P2)[0]

    assert cast_skill(engine, fanying, "fanying_skill3", ally)
    assert effects_of(ally, EffectType.buff_damage_percent_boost)
    assert cast_skill(engine, fanying, "fanying_skill3", enemy)
    assert effects_of(enemy, EffectType.debuff_stun)


def test_your_turn_self_target_advances_next_turn_and_keeps_buff(engine_factory):
    engine = engine_factory(("fanying", "flora", "clawdragon", "chaosling", "starweaver"))
    fanying = by_template(engine, P1, "fanying")

    assert cast_skill(engine, fanying, "fanying_skill3", fanying)

    assert engine.state.active_actor_id == fanying.unique_id
    assert effects_of(fanying, EffectType.buff_damage_percent_boost)
