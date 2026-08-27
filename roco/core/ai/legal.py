"""Enumerate actions that pass the engine's own validation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..battle.actions import ActionDict
from ..battle.engine import BattleEngine
from ..battle.types import ActionType, BattleSpirit, TargetType
from ..spirits import get_spirit_logic, get_spirit_template
from ..spirits.guifashi_cards import ALLY_TARGET_CARDS, ENEMY_TARGET_CARDS, TAROT_CARDS
from ..spirits.guifashi_support import get_cards


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


def _guifashi_skill_actions(
    engine: BattleEngine,
    player_id: str,
    actor: BattleSpirit,
    skill,
) -> List[Dict[str, Any]]:
    """Enumerate card-specific actions for 诡法师."""
    state = get_cards(actor)
    if skill.id == "guifashi_draw":
        action = _base(actor, ActionType.use_skill.value, skillId=skill.id)
        # 与揭晓/逆位一致：必须过引擎校验（能量、额外行动策略等），
        # 否则能量不足时仍会被 AI 选中，导致反复「行动未通过校验」。
        return [action] if engine._validate_action(player_id, action, actor) else []

    if skill.id == "guifashi_show":
        actions: List[Dict[str, Any]] = []
        opponent_id = engine.get_opponent_id(player_id)
        enemies = _alive(engine.get_all_spirits(opponent_id))
        allies = _alive(engine.get_all_spirits(player_id))
        for idx, card in enumerate(state.hand):
            extra: Dict[str, Any] = {"skillId": skill.id, "cardHandIndex": idx}
            if card in ALLY_TARGET_CARDS:
                targets = [a.unique_id for a in allies] or [None]
            elif card in ENEMY_TARGET_CARDS:
                targets = [e.unique_id for e in enemies] or [None]
            elif card == "demon":
                consume = [i for i in range(len(state.hand)) if i != idx]
                if not consume:
                    continue
                extra["consumeHandIndices"] = consume
                targets = [None]
            else:
                targets = [None]
            for tid in targets:
                action = _base(actor, ActionType.use_skill.value, **extra)
                if tid is not None:
                    action["targetId"] = tid
                if engine._validate_action(player_id, action, actor):
                    actions.append(action)
        return actions

    if skill.id == "guifashi_cheat":
        actions: List[Dict[str, Any]] = []
        for idx, old_card in enumerate(state.hand):
            for new_card in TAROT_CARDS:
                if new_card == old_card:
                    continue
                action = _base(
                    actor,
                    ActionType.use_skill.value,
                    skillId=skill.id,
                    cardHandIndex=idx,
                    newCardId=new_card,
                )
                if engine._validate_action(player_id, action, actor):
                    actions.append(action)
        return actions

    return []


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

    logic = get_spirit_logic(actor.template_id)
    for skill in tpl.skills:
        if actor.template_id == "guifashi" and skill.id in {"guifashi_draw", "guifashi_show", "guifashi_cheat"}:
            skill_actions = _guifashi_skill_actions(engine, player_id, actor, skill)
            candidates.extend(skill_actions)
            continue
        tt = skill.target_type
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
