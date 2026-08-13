"""Pure battle logic — no UI dependencies."""

from .battle.engine import BattleEngine, create_battle_spirit
from .battle.rules import MAX_TEAM_SIZE, MIN_TEAM_SIZE

__all__ = [
    "BattleEngine",
    "MAX_TEAM_SIZE",
    "MIN_TEAM_SIZE",
    "create_battle_spirit",
]
