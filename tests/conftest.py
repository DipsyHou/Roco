from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from roco.core.battle.engine import BattleEngine
from roco.core.battle.types import ActionType, BattleSpirit, EffectType
from roco.core.spirits import get_spirit_template

P1 = "p1"
P2 = "p2"
DEFAULT_P1 = ("flora", "clawdragon", "chaosling", "starweaver", "steamdragon")
DEFAULT_P2 = ("qiuka", "fanying", "tita", "guifashi", "flora")


def templates(*ids: str):
    return [get_spirit_template(template_id) for template_id in ids]


def make_engine(
    p1_ids: tuple[str, ...] = DEFAULT_P1,
    p2_ids: tuple[str, ...] = DEFAULT_P2,
    battle_id: str = "test-battle",
) -> BattleEngine:
    return BattleEngine(battle_id, P1, P2, templates(*p1_ids), templates(*p2_ids))


def all_spirits(engine: BattleEngine) -> list[BattleSpirit]:
    return engine.get_all_spirits(P1) + engine.get_all_spirits(P2)


def by_template(engine: BattleEngine, player_id: str, template_id: str) -> BattleSpirit:
    return next(s for s in engine.get_all_spirits(player_id) if s.template_id == template_id)


def active_spirit(engine: BattleEngine) -> BattleSpirit:
    actor_id = engine.state.active_actor_id
    assert actor_id is not None
    actor = engine.find_spirit_anywhere(actor_id)
    assert actor is not None
    return actor


def action_for(actor: BattleSpirit, action_type: str, **payload: Any) -> dict[str, Any]:
    return {
        "type": action_type,
        "playerId": actor.owner_id,
        "actorId": actor.unique_id,
        **payload,
    }


def submit(engine: BattleEngine, actor: BattleSpirit, action_type: str, **payload: Any) -> bool:
    return engine.submit_action(actor.owner_id, action_for(actor, action_type, **payload))


def skip_active(engine: BattleEngine) -> bool:
    actor = active_spirit(engine)
    return submit(engine, actor, ActionType.skip.value)


def advance_to(engine: BattleEngine, actor: BattleSpirit, max_steps: int = 200) -> None:
    for _ in range(max_steps):
        if engine.state.phase.value == "finished":
            raise AssertionError("battle finished before target actor became active")
        if engine.state.active_actor_id == actor.unique_id:
            return
        assert skip_active(engine)
    raise AssertionError(f"{actor.template_id} did not become active within {max_steps} steps")


def cast_skill(
    engine: BattleEngine,
    actor: BattleSpirit,
    skill_id: str,
    target: BattleSpirit | None = None,
    **payload: Any,
) -> bool:
    advance_to(engine, actor)
    if target is not None:
        payload.setdefault("targetId", target.unique_id)
    return submit(engine, actor, ActionType.use_skill.value, skillId=skill_id, **payload)


def normal_attack(engine: BattleEngine, actor: BattleSpirit, target: BattleSpirit) -> bool:
    advance_to(engine, actor)
    return submit(engine, actor, ActionType.normal_attack.value, targetId=target.unique_id)


def effects_of(spirit: BattleSpirit, effect_type: EffectType):
    return [effect for effect in spirit.effects if effect.type == effect_type]


@pytest.fixture
def engine_factory() -> Callable[..., BattleEngine]:
    return make_engine


@pytest.fixture
def standard_engine() -> BattleEngine:
    return make_engine()
