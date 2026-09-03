from __future__ import annotations

from tests.conftest import P1, by_template, cast_skill, effects_of, skip_active
from roco.core.battle.types import EffectType, StatType


def test_shunt_is_stack_state_and_decays_on_turn_start(engine_factory):
    engine = engine_factory(("tita", "flora", "clawdragon", "chaosling", "starweaver"))
    tita = by_template(engine, P1, "tita")

    assert cast_skill(engine, tita, "tita_skill1")
    shunt = effects_of(tita, EffectType.state_shunt)[0]
    assert shunt.stacks == 2

    while engine.state.active_actor_id != tita.unique_id:
        assert skip_active(engine)
    engine.ensure_active_turn_begun()

    assert effects_of(tita, EffectType.state_shunt)[0].stacks == 1


def test_expansion_passive_increases_team_energy_cap_on_battle_start(engine_factory):
    engine = engine_factory(("tita", "flora", "clawdragon", "chaosling", "starweaver"))

    assert engine.state.players[P1].max_team_energy == 12


def test_overload_slows_enemy_and_self(engine_factory):
    engine = engine_factory(("tita", "flora", "clawdragon", "chaosling", "starweaver"))
    tita = by_template(engine, P1, "tita")
    enemy = engine.get_active_spirits("p2")[0]

    assert cast_skill(engine, tita, "tita_skill2", enemy)

    enemy_slow = effects_of(enemy, EffectType.debuff_stat_percent_reduction)[0]
    self_slow = effects_of(tita, EffectType.debuff_stat_percent_reduction)[0]
    assert enemy_slow.stat_type == StatType.speed
    assert enemy_slow.value == 0.20
    assert enemy_slow.duration_turns == 2
    assert self_slow.duration_turns == 1
