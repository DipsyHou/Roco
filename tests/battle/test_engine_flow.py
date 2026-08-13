from __future__ import annotations

from roco.core.battle.effects import make_effect
from roco.core.battle.timeline import ACTION_GAP
from roco.core.battle.types import ActionType, BattleLogType, BattlePhase, EffectType
from roco.core.spirit_logic import SpiritLogic
from roco.core.spirits import registry


class HookRecorder(SpiritLogic):
    template_id = "flora"

    def __init__(self, events: list[tuple[str, str]]) -> None:
        self.events = events

    def on_turn_start(self, ctx, actor):  # noqa: ANN001
        self.events.append(("turn_start", actor.unique_id))

    def on_turn_end(self, ctx, player_id, actor, action, *, stunned=False):  # noqa: ANN001
        self.events.append(("turn_end_stunned" if stunned else "turn_end", actor.unique_id))

    def on_ally_turn_end(self, ctx, player_id, observer, actor):  # noqa: ANN001
        self.events.append(("ally_turn_end", observer.unique_id))

    def on_passive_check(self, ctx, player_id):  # noqa: ANN001
        self.events.append(("passive", player_id))


def test_wrong_actor_action_is_rejected(standard_engine):
    active = standard_engine.find_spirit_anywhere(standard_engine.state.active_actor_id)
    other = next(s for s in standard_engine.get_all_spirits("p1") if s.unique_id != active.unique_id)

    ok = standard_engine.submit_action(
        other.owner_id,
        {"type": ActionType.skip.value, "playerId": other.owner_id, "actorId": other.unique_id},
    )

    assert not ok


def test_stunned_actor_still_runs_turn_hooks(monkeypatch, engine_factory):
    events: list[tuple[str, str]] = []
    monkeypatch.setitem(registry._REGISTRY, "flora", HookRecorder(events))
    engine = engine_factory(("flora",) * 5, ("flora",) * 5)
    actor = engine.find_spirit_anywhere(engine.state.active_actor_id)
    actor.effects.append(make_effect(EffectType.debuff_stun, "src", duration_turns=1))

    assert engine.submit_action(
        actor.owner_id,
        {"type": ActionType.skip.value, "playerId": actor.owner_id, "actorId": actor.unique_id},
    )

    kinds = [kind for kind, _ in events]
    assert "turn_start" in kinds
    assert "turn_end_stunned" in kinds
    assert kinds.count("passive") == 2
    assert kinds.count("ally_turn_end") == 5


def test_submit_action_finishes_battle_when_last_enemy_falls(engine_factory):
    engine = engine_factory(("clawdragon",) * 5, ("qiuka",) * 5)
    attacker = engine.get_all_spirits("p1")[0]
    target = engine.get_all_spirits("p2")[0]
    for spirit in engine.get_all_spirits("p2")[1:]:
        spirit.is_alive = False
        spirit.current_hp = 0
    attacker.base_stats.atk = 9999
    target.current_hp = 1
    attacker.charge = 0
    target.charge = ACTION_GAP
    engine.state.active_actor_id = attacker.unique_id

    assert engine.submit_action(
        "p1",
        {
            "type": ActionType.normal_attack.value,
            "playerId": "p1",
            "actorId": attacker.unique_id,
            "targetId": target.unique_id,
        },
    )

    assert engine.state.phase == BattlePhase.finished
    assert engine.state.winner_id == "p1"
    assert engine.state.battle_log[-1].type == BattleLogType.battle_end


def test_timeline_preview_matches_first_real_actor(standard_engine):
    first_preview = standard_engine.state.timeline_preview[0]

    while standard_engine.state.active_actor_id != first_preview:
        actor = standard_engine.find_spirit_anywhere(standard_engine.state.active_actor_id)
        assert actor is not None
        assert standard_engine.submit_action(
            actor.owner_id,
            {"type": ActionType.skip.value, "playerId": actor.owner_id, "actorId": actor.unique_id},
        )

    assert standard_engine.state.active_actor_id == first_preview
