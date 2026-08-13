"""Battle engine, types, rules, and turn pipeline."""

from .engine import BattleEngine, create_battle_spirit
from .events import DamageEvent, DamageSource, dispatch_damage
from .rules import (
    MAX_TEAM_SIZE,
    MIN_TEAM_SIZE,
    TEAM_ENERGY_CAP_MAX,
    TEAM_ENERGY_MAX,
    TEAM_GATHER_ENERGY_GAIN,
)
from .turn_pipeline import TurnPipeline

__all__ = [
    "BattleEngine",
    "DamageEvent",
    "DamageSource",
    "TurnPipeline",
    "MAX_TEAM_SIZE",
    "MIN_TEAM_SIZE",
    "TEAM_ENERGY_MAX",
    "TEAM_ENERGY_CAP_MAX",
    "TEAM_GATHER_ENERGY_GAIN",
    "create_battle_spirit",
    "dispatch_damage",
]
