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
        # Should be unreachable if skip is always legal for living actors.
        return {
            "type": "skip",
            "playerId": player_id,
            "actorId": actor.unique_id,
        }

    policy = POLICY_BY_TEMPLATE.get(actor.template_id)
    return pick_by_score(engine, actor, actions, policy)
