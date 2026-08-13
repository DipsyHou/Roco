"""Policy protocol and default scorer."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from ...battle.engine import BattleEngine
from ...battle.types import ActionType, BattleSpirit
from .. import features as F


class SpiritPolicy(Protocol):
    template_id: str

    def score(
        self,
        engine: BattleEngine,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> float: ...


def default_score(
    engine: BattleEngine,
    actor: BattleSpirit,
    action: Dict[str, Any],
) -> float:
    """Fallback for spirits without a dedicated policy."""
    at = action.get("type")
    energy = F.team_energy(engine, actor.owner_id)
    if at == ActionType.gather_energy.value:
        return 40.0 if energy <= 3 else 5.0
    if at == ActionType.skip.value:
        return -100.0
    if at == ActionType.normal_attack.value:
        target = engine.find_spirit_anywhere(action.get("targetId") or "")
        if not target:
            return 10.0
        return 20.0 + max(0, 30 - target.current_hp / 20)
    if at == ActionType.use_skill.value:
        return 25.0 if energy >= 2 else 0.0
    return 0.0


def pick_by_score(
    engine: BattleEngine,
    actor: BattleSpirit,
    actions: List[Dict[str, Any]],
    policy: Optional[SpiritPolicy],
) -> Dict[str, Any]:
    if not actions:
        raise ValueError("no legal actions")
    best = actions[0]
    best_score = float("-inf")
    for action in actions:
        if policy is not None:
            score = policy.score(engine, actor, action)
        else:
            score = default_score(engine, actor, action)
        if score > best_score:
            best_score = score
            best = action
    return best
