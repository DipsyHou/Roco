from __future__ import annotations

from roco.core.battle.engine import BattleEngine
from roco.core.battle.effects import make_effect
from roco.core.battle.types import (
    ActionType,
    BattleLogType,
    BattlePhase,
    EffectType,
    PresentationStage,
)
from roco.core.spirits import get_spirit_template
from roco.net.serialize import state_from_dict, state_to_dict
from tests.conftest import P1, P2


P1_IDS = ("clawdragon", "flora", "chaosling", "starweaver", "steamdragon")
P2_IDS = ("qiuka", "fanying", "tita", "guifashi", "flora")


def staged_engine() -> BattleEngine:
    return BattleEngine(
        "presentation-test",
        P1,
        P2,
        [get_spirit_template(value) for value in P1_IDS],
        [get_spirit_template(value) for value in P2_IDS],
        presentation_windows=True,
    )


def advance_to_normal_action(engine: BattleEngine) -> None:
    assert engine.state.presentation_stage == PresentationStage.turn_start
    assert engine.advance_presentation(engine.state.presentation_token)
    assert engine.state.phase == BattlePhase.presentation
    assert engine.state.presentation_stage == PresentationStage.normal_action
    assert engine.advance_presentation(engine.state.presentation_token)
    assert engine.state.phase == BattlePhase.waiting_for_action


def test_presentation_rejects_stale_token_and_reaches_turn_end() -> None:
    engine = staged_engine()
    engine.ensure_active_turn_begun()
    start_token = engine.state.presentation_token
    assert engine.advance_presentation(start_token)
    assert not engine.advance_presentation(start_token)
    assert engine.advance_presentation(engine.state.presentation_token)
    actor = engine.find_spirit_anywhere(engine.state.active_actor_id or "")
    assert actor is not None

    assert engine.submit_action(
        actor.owner_id,
        {
            "type": ActionType.skip.value,
            "playerId": actor.owner_id,
            "actorId": actor.unique_id,
        },
    )
    assert engine.advance_presentation(engine.state.presentation_token)
    assert engine.state.presentation_stage == PresentationStage.turn_end

    assert engine.advance_presentation(engine.state.presentation_token)
    assert engine.state.phase in (BattlePhase.presentation, BattlePhase.waiting_for_action)


def test_structured_presentation_events_are_not_parsed_from_messages() -> None:
    engine = staged_engine()
    target = engine.get_all_spirits(P2)[0]
    engine.add_log(
        BattleLogType.damage_dealt,
        "arbitrary localized text",
        {"targetId": target.unique_id, "damage": 17},
    )

    event = engine.state.presentation_events[-1]
    assert event.kind == "damage"
    assert event.target_id == target.unique_id
    assert event.amount == 17
    assert event.log_index == len(engine.state.battle_log) - 1
    assert event.current_hp == target.current_hp
    assert event.max_hp == target.max_hp

    restored = state_from_dict(state_to_dict(engine.state))
    restored_event = restored.presentation_events[-1]
    assert restored_event == event
    assert restored.presentation_stage == engine.state.presentation_stage
    assert restored.presentation_token == engine.state.presentation_token


def test_presentation_event_roundtrip_keeps_detail_effect_snapshot() -> None:
    engine = staged_engine()
    target = engine.get_all_spirits(P2)[0]
    effect = make_effect(EffectType.debuff_burn, "source", stacks=3)
    target.effects.append(effect)

    engine.add_log(
        BattleLogType.effect_applied,
        "effect",
        {
            "targetId": target.unique_id,
            "effectId": effect.id,
            "effectType": effect.type.value,
            "sourceId": effect.source_id,
        },
    )

    event = engine.state.presentation_events[-1]
    assert [item.id for item in event.effects] == [effect.id]
    restored = state_from_dict(state_to_dict(engine.state))
    assert [item.id for item in restored.presentation_events[-1].effects] == [effect.id]
