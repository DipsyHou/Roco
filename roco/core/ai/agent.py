"""AI entry: pick one legal action for the active actor."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..battle.engine import BattleEngine
from ..battle.types import BattleSpirit
from .legal import enumerate_legal_actions
from .policies import POLICY_BY_TEMPLATE
from .policies.base import pick_by_score


def choose_action(
    engine: BattleEngine,
    player_id: str,
    *,
    actor: Optional[BattleSpirit] = None,
) -> Dict[str, Any]:
    """Return a legal action dict for ``player_id``'s current active spirit.

    Spirits with a registered policy use heuristics; others use the default scorer.
    """
    if actor is None:
        actor_id = engine.state.active_actor_id
        if not actor_id:
            raise RuntimeError("no active actor")
        actor = engine.find_spirit_anywhere(actor_id)
    if not actor or actor.owner_id != player_id:
        raise RuntimeError("active actor is not owned by player")

    actions = enumerate_legal_actions(engine, player_id, actor=actor)
    if not actions:
        # Unreachable when skip is legal. Policies that forbid skip must still
        # expose a legal skill; a silent skip here can loop-fail validation.
        raise RuntimeError(
            f"no legal actions for {actor.template_id} "
            f"(extra_slot={engine.current_extra_slot()})"
        )

    policy = POLICY_BY_TEMPLATE.get(actor.template_id)
    return pick_by_score(engine, actor, actions, policy)
