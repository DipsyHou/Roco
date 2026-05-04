"""Per-spirit skill hooks — mirror TS SpiritLogic + BattleContext."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Protocol

from .battle_types import BattleLogType, BattleSpirit

if TYPE_CHECKING:
    from .engine import BattleEngine


class BattleContext(Protocol):
    def get_opponent_id(self, player_id: str) -> str: ...
    def find_spirit(self, player_id: str, unique_id: str) -> Optional["BattleSpirit"]: ...
    def find_spirit_anywhere(self, unique_id: str) -> Optional["BattleSpirit"]: ...
    def get_field_spirits(self, player_id: str) -> list: ...
    def get_all_spirits(self, player_id: str) -> list: ...
    def add_log(
        self,
        log_type: Any,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None: ...
    def execute_normal_attack(
        self,
        player_id: str,
        action: Dict[str, Any],
        is_auto_triggered: bool = False,
    ) -> None: ...
    def trigger_starweaver_passive(self, player_id: str, target: "BattleSpirit") -> None: ...


class SpiritLogic:
    template_id: str

    def on_init(self, spirit: "BattleSpirit") -> None:
        pass

    def execute_skill(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: "BattleSpirit",
        action: Dict[str, Any],
    ) -> None:
        raise NotImplementedError

    def on_after_skill(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: "BattleSpirit",
    ) -> None:
        pass

    def on_after_normal_attack(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: "BattleSpirit",
        is_auto_triggered: bool,
    ) -> None:
        pass

    def check_passive(self, ctx: BattleContext, player_id: str) -> None:
        pass

    def on_end_of_turn(self, ctx: BattleContext, spirit: "BattleSpirit") -> None:
        pass
