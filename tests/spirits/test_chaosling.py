from __future__ import annotations

from tests.conftest import P1, by_template, cast_skill, effects_of, skip_active
from roco.core.battle.types import EffectType, StatType


def test_rage_starts_channel_and_applies_first_stage_modifiers(engine_factory):
    engine = engine_factory(("chaosling", "flora", "clawdragon", "starweaver", "steamdragon"))
    chaos = by_template(engine, P1, "chaosling")

    assert cast_skill(engine, chaos, "chaosling_skill1")

    channel = effects_of(chaos, EffectType.state_channeling_skill)[0]
    assert channel.channel_skill_id == "chaosling_skill1"
    assert channel.channel_phase == 1
    assert any(e.stat_type == StatType.atk for e in effects_of(chaos, EffectType.buff_stat_percent_boost))
    assert any(e.stat_type == StatType.mag_atk for e in effects_of(chaos, EffectType.debuff_stat_percent_reduction))


def test_channel_advances_at_turn_start_even_if_stunned(engine_factory):
    from roco.core.battle.effects import make_effect

    engine = engine_factory(("chaosling", "flora", "clawdragon", "starweaver", "steamdragon"))
    chaos = by_template(engine, P1, "chaosling")
    assert cast_skill(engine, chaos, "chaosling_skill1")
    chaos.effects.append(make_effect(EffectType.debuff_stun, "x", duration_turns=1))

    while engine.state.active_actor_id != chaos.unique_id:
        assert skip_active(engine)

    engine.ensure_active_turn_begun()
    channel = effects_of(chaos, EffectType.state_channeling_skill)[0]
    assert channel.channel_phase == 2


def test_reverse_turns_stat_debuffs_into_buffs(engine_factory):
    engine = engine_factory(("chaosling", "flora", "clawdragon", "starweaver", "steamdragon"))
    chaos = by_template(engine, P1, "chaosling")
    enemy = engine.get_active_spirits("p2")[0]
    assert cast_skill(engine, chaos, "chaosling_skill1")

    assert cast_skill(engine, chaos, "chaosling_skill3", enemy)

    assert any(
        effect.display_name == "命运逆转"
        for effect in effects_of(chaos, EffectType.buff_stat_percent_boost)
    )
