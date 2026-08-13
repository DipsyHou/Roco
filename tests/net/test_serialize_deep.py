from __future__ import annotations

from copy import deepcopy

from tests.conftest import P1, by_template
from roco.core.battle.effects import make_effect
from roco.core.battle.types import BattleLogType, BattlePhase, DamageType, EffectType, StatType
from roco.core.battle.extra_action import ExtraActionSlot
from roco.core.spirits.guifashi_cards import CardState
from roco.net.serialize import effect_from_dict, state_from_dict, state_to_dict


def test_state_roundtrip_preserves_runtime_fields(engine_factory):
    engine = engine_factory(("guifashi", "flora", "clawdragon", "chaosling", "starweaver"))
    guifashi = by_template(engine, P1, "guifashi")
    guifashi.current_hp -= 123
    guifashi.charge = 4321.5
    guifashi.effects.append(
        make_effect(
            EffectType.buff_damage_percent_boost,
            "src",
            duration_turns=2,
            stacks=0,
            damage_type=DamageType.physical,
            value=0.2,
            display_name="test",
        )
    )
    guifashi.card_state = CardState(deck=["sun"], hand=["moon"], pending_moon_energy=True).to_dict()
    engine.state.extra_action_queue = [
        ExtraActionSlot(actor_id=guifashi.unique_id, policy_id="guifashi_chain", source="guifashi_chain")
    ]
    engine.state.active_turn_stunned = True
    engine.state.winner_id = "p1"
    engine.state.phase = BattlePhase.finished
    engine.add_log(BattleLogType.effect_applied, "serialize me", {"k": "v"})

    raw = state_to_dict(engine.state)
    restored = state_from_dict(deepcopy(raw))
    restored_spirit = next(s for s in restored.players[P1].spirits if s.unique_id == guifashi.unique_id)

    assert raw["players"][P1]["spirits"][0]["effects"][0]["durationTurns"] == 2
    assert raw["players"][P1]["spirits"][0]["effects"][0]["stacks"] == 0
    assert restored.phase == BattlePhase.finished
    assert restored.winner_id == "p1"
    assert len(restored.extra_action_queue) == 1
    assert restored.extra_action_queue[0].actor_id == guifashi.unique_id
    assert restored.extra_action_queue[0].policy_id == "guifashi_chain"
    assert restored.active_turn_stunned
    assert restored.timeline_preview == engine.state.timeline_preview
    assert restored.battle_log[-1].data == {"k": "v"}
    assert restored_spirit.current_hp == guifashi.current_hp
    assert restored_spirit.charge == guifashi.charge
    assert restored_spirit.card_state == guifashi.card_state


def test_state_roundtrip_preserves_sync_attrs(engine_factory):
    from roco.core.spirits.tengjiao import PENDING_FREE_KEY, _set_pending_free

    engine = engine_factory(("tengjiao", "flora", "clawdragon", "chaosling", "starweaver"))
    tengjiao = by_template(engine, P1, "tengjiao")
    _set_pending_free(tengjiao, ["laziji", "shuizhuyu"])

    raw = state_to_dict(engine.state)
    restored = state_from_dict(deepcopy(raw))
    restored_spirit = next(s for s in restored.players[P1].spirits if s.unique_id == tengjiao.unique_id)

    assert raw["players"][P1]["spirits"][0]["syncAttrs"][PENDING_FREE_KEY] == [
        "laziji",
        "shuizhuyu",
    ]
    assert restored_spirit.sync_attrs[PENDING_FREE_KEY] == ["laziji", "shuizhuyu"]


def test_legacy_remaining_turns_maps_to_duration_for_duration_effects():
    effect = effect_from_dict(
        {
            "id": "e1",
            "type": EffectType.debuff_stun.value,
            "sourceId": "src",
            "remainingTurns": 2,
            "statType": StatType.speed.value,
        }
    )

    assert effect.duration_turns == 2
    assert effect.stacks == 0


def test_legacy_remaining_turns_maps_to_stacks_for_stack_effects():
    effect = effect_from_dict(
        {
            "id": "e1",
            "type": EffectType.debuff_burn.value,
            "sourceId": "src",
            "remainingTurns": 4,
        }
    )

    assert effect.duration_turns is None
    assert effect.stacks == 4
