"""Pure battle logic — no UI dependencies."""

from .battle.engine import BattleEngine, create_battle_spirit
from .battle.rules import MIN_TEAM_SIZE

__all__ = [
    "BattleEngine",
    "MIN_TEAM_SIZE",
    "create_battle_spirit",
]
