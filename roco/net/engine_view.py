"""Read-only engine surface shared by the UI.

Both :class:`roco.core.battle.engine.BattleEngine` (authoritative, local) and
:class:`roco.net.remote_engine.RemoteBattleEngine` (server-synced mirror) satisfy
this :class:`typing.Protocol` structurally. UIs should depend on ``EngineView``
instead of branching on ``isinstance(eng, RemoteBattleEngine)`` or reaching into
private attributes like ``_player_ids_list``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from roco.core.battle.types import BattleSpirit, BattleState


@runtime_checkable
class EngineView(Protocol):
    """The subset of the engine API the desktop UI reads."""

    state: BattleState

    @property
    def player_ids(self) -> List[str]: ...

    def get_opponent_id(self, player_id: str) -> str: ...

    def find_spirit(self, player_id: str, unique_id: str) -> Optional[BattleSpirit]: ...

    def find_spirit_anywhere(self, unique_id: str) -> Optional[BattleSpirit]: ...

    def get_active_spirits(self, player_id: str) -> List[BattleSpirit]: ...

    def get_adjacent_enemies(self, target: BattleSpirit) -> List[BattleSpirit]: ...

    def get_adjacent_allies(
        self, anchor: BattleSpirit, player_id: str
    ) -> List[BattleSpirit]: ...

    def get_effective_speed(self, spirit: BattleSpirit) -> float: ...

    def effective_skill_energy_cost(self, actor: BattleSpirit, skill: Any) -> int: ...

    def current_extra_slot(self) -> Any: ...

    def ensure_active_turn_begun(self) -> None: ...

    def submit_action(self, player_id: str, action: Dict[str, Any]) -> bool: ...
