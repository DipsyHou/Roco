"""Battle collaboration interfaces.

``BattleContext`` is the spirit-facing surface (what ``SpiritLogic`` hooks may
call). ``TurnHost`` adds the engine-internal collaboration methods used by the
turn pipeline, damage events, and HP helpers — these must not be called from
spirit logic.

Both are :class:`typing.Protocol`s: the concrete implementation is
``BattleEngine``. Keeping them here (rather than a hand-written stub class)
gives a single source of truth and lets type checkers verify the boundary.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Protocol

from .actions import ActionDict
from .events import DamageSource
from .extra_action import ExtraActionSlot
from .types import BattleLogType, BattleSpirit, BattleState, DamageType


class BattleContext(Protocol):
    """Surface available to spirit logic during a battle."""

    state: BattleState

    @property
    def battle_id(self) -> str: ...

    def next_rng(self, domain: str, *parts: Any) -> random.Random: ...

    def get_opponent_id(self, player_id: str) -> str: ...

    def find_spirit(self, player_id: str, unique_id: str) -> Optional[BattleSpirit]: ...

    def find_spirit_anywhere(self, unique_id: str) -> Optional[BattleSpirit]: ...

    def get_active_spirits(self, player_id: str) -> List[BattleSpirit]: ...

    def get_all_spirits(self, player_id: str) -> List[BattleSpirit]: ...

    def get_adjacent_enemies(self, target: BattleSpirit) -> List[BattleSpirit]: ...

    def get_adjacent_allies(
        self, anchor: BattleSpirit, player_id: str
    ) -> List[BattleSpirit]: ...

    def add_log(
        self,
        log_type: BattleLogType,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None: ...

    def execute_normal_attack(
        self,
        player_id: str,
        action: ActionDict,
        is_auto_triggered: bool = False,
    ) -> None: ...

    def notify_damage_taken(
        self,
        attacker: Optional[BattleSpirit],
        target: BattleSpirit,
        damage: int,
        *,
        source: DamageSource = DamageSource.other,
    ) -> None: ...

    def advance_action(self, target: BattleSpirit, percent: float) -> None: ...

    def delay_action(self, target: BattleSpirit, percent: float) -> None: ...

    def gain_team_energy(
        self,
        player_id: str,
        amount: int,
        *,
        reason: Optional[str] = None,
        log_type: Any = None,
        silent: bool = False,
    ) -> int: ...

    def sync_team_energy_cap(self, player_id: str) -> int: ...

    def get_team_energy_spent(self, player_id: str) -> int: ...

    def reset_team_energy_spent(self, player_id: str) -> None: ...

    def queue_extra_actions(
        self,
        slots: List[ExtraActionSlot],
        *,
        front: bool = False,
    ) -> None: ...

    def current_extra_slot(self) -> Optional[ExtraActionSlot]: ...


class TurnHost(BattleContext, Protocol):
    """Engine-internal collaboration surface for pipeline / events / hp."""

    @property
    def player_ids(self) -> List[str]: ...

    def execute_action(self, player_id: str, action: ActionDict) -> None: ...

    def log_effect_expired(self, spirit: BattleSpirit, eff: Any) -> None: ...

    def after_actor_acts(self, actor: BattleSpirit) -> None: ...

    def notify_spirit_defeated(self, defeated: BattleSpirit) -> None: ...
