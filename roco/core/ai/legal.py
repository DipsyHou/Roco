"""Enumerate actions that pass the engine's own validation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..battle.actions import ActionDict
from ..battle.engine import BattleEngine
from ..battle.types import ActionType, BattleSpirit, TargetType
from ..spirits import get_spirit_logic, get_spirit_template


def _base(actor: BattleSpirit, action_type: str, **extra: Any) -> Dict[str, Any]:
    return {
        "type": action_type,
        "playerId": actor.owner_id,
        "actorId": actor.unique_id,
        **extra,
    }


def _alive(spirits: List[BattleSpirit]) -> List[BattleSpirit]:
    return [s for s in spirits if s.is_alive]


def expand_targets(
    engine: BattleEngine,
    actor: BattleSpirit,
    target_type: TargetType,
) -> List[Optional[str]]:
    """Return candidate targetId values (None = no target field)."""
    allies = _alive(engine.get_all_spirits(actor.owner_id))
    enemies = _alive(engine.get_all_spirits(engine.get_opponent_id(actor.owner_id)))

    if target_type == TargetType.none:
        return [None]
    if target_type == TargetType.self:
        return [actor.unique_id]
    if target_type in (TargetType.all_enemies, TargetType.all_allies):
        return [None]
    if target_type in (TargetType.single_enemy, TargetType.any_on_field):
        return [e.unique_id for e in enemies] or [None]
    if target_type in (TargetType.single_ally, TargetType.single_ally_on_field):
        return [a.unique_id for a in allies] or [None]
    return [None]


def enumerate_legal_actions(
    engine: BattleEngine,
    player_id: str,
    *,
    actor: Optional[BattleSpirit] = None,
) -> List[Dict[str, Any]]:
    """List legal actions for the current active actor of ``player_id``."""
    if engine.state.phase.value != "waiting_for_action":
        return []
    actor_id = engine.state.active_actor_id
    if not actor_id:
        return []
    if actor is None:
        actor = engine.find_spirit_anywhere(actor_id)
    if not actor or actor.owner_id != player_id or actor.unique_id != actor_id:
        return []

    candidates: List[Dict[str, Any]] = []

    for action in (
        _base(actor, ActionType.skip.value),
        _base(actor, ActionType.gather_energy.value),
    ):
        if engine._validate_action(player_id, action, actor):
            candidates.append(action)

    tpl = get_spirit_template(actor.template_id)
    if not tpl:
        return candidates

    for enemy in _alive(engine.get_all_spirits(engine.get_opponent_id(player_id))):
        action = _base(
            actor,
            ActionType.normal_attack.value,
            targetId=enemy.unique_id,
        )
        if engine._validate_action(player_id, action, actor):
            candidates.append(action)

    for skill in tpl.skills:
        tt = skill.target_type
        logic = get_spirit_logic(actor.template_id)
        if logic:
            override = logic.get_skill_target_type(engine, actor, skill)
            if override is not None:
                tt = override
        for tid in expand_targets(engine, actor, tt):
            extra: Dict[str, Any] = {"skillId": skill.id}
            if tid is not None:
                extra["targetId"] = tid
            action = _base(actor, ActionType.use_skill.value, **extra)
            if engine._validate_action(player_id, action, actor):
                candidates.append(action)

    return candidates
