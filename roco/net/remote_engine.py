"""Client-side facade with the subset of BattleEngine API used by desktop UI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from roco.core.battle.types import BattlePhase, BattleSpirit, BattleState, StatType
from roco.core.battle.stats import bind_spirit_stat_engine
from roco.core.battle.formation import living_slot_neighbors
from roco.core.battle.utils import get_effective_stat
from .client import BattleNetClient
from .protocol import MSG_SUBMIT_ACTION, MSG_SYNC_TURN
from .serialize import state_from_dict


class RemoteBattleEngine:
    """Mirror of local engine surface; state is synced from server."""

    def __init__(self, client: BattleNetClient, my_player_id: str) -> None:
        self._client = client
        self.my_player_id = my_player_id
        self.state = BattleState(
            battle_id="",
            phase=BattlePhase.waiting_for_action,
            action_count=0,
            players={},
        )
        self._effective_speeds: Dict[str, int] = {}
        self._player_ids: List[str] = ["p1", "p2"]

    def apply_server_snapshot(
        self,
        state_dict: Dict[str, Any],
        effective_speeds: Dict[str, int],
        player_ids: Optional[List[str]] = None,
    ) -> None:
        self.state = state_from_dict(state_dict)
        self._effective_speeds = {str(k): int(v) for k, v in effective_speeds.items()}
        if player_ids:
            self._player_ids = player_ids
        for pid in self._player_ids_list:
            for spirit in self.get_all_spirits(pid):
                bind_spirit_stat_engine(spirit, self)

    @property
    def _player_ids_list(self) -> List[str]:
        if self.state.players:
            keys = list(self.state.players.keys())
            if len(keys) >= 2:
                return keys[:2]
        return self._player_ids

    @property
    def player_ids(self) -> List[str]:
        """Public, ordered player ids (mirrors ``BattleEngine.player_ids``)."""
        return self._player_ids_list

    def get_all_spirits(self, player_id: str) -> List[BattleSpirit]:
        pd = self.state.players.get(player_id)
        if not pd:
            return []
        return list(pd.spirits)

    def get_opponent_id(self, player_id: str) -> str:
        return next(pid for pid in self._player_ids_list if pid != player_id)

    def find_spirit(self, player_id: str, unique_id: str) -> Optional[BattleSpirit]:
        pd = self.state.players.get(player_id)
        if not pd:
            return None
        return next((s for s in pd.spirits if s.unique_id == unique_id), None)

    def find_spirit_anywhere(self, unique_id: str) -> Optional[BattleSpirit]:
        for pid in self._player_ids_list:
            s = self.find_spirit(pid, unique_id)
            if s:
                return s
        return None

    def get_active_spirits(self, player_id: str) -> List[BattleSpirit]:
        pd = self.state.players.get(player_id)
        if not pd:
            return []
        return [s for s in pd.spirits if s.is_alive]

    def get_adjacent_enemies(self, target: BattleSpirit) -> List[BattleSpirit]:
        return living_slot_neighbors(self.get_active_spirits(target.owner_id), target)

    def get_adjacent_allies(
        self, anchor: BattleSpirit, player_id: str
    ) -> List[BattleSpirit]:
        return [anchor] + living_slot_neighbors(
            self.get_active_spirits(player_id), anchor
        )

    def get_effective_speed(self, spirit: BattleSpirit) -> float:
        cached = self._effective_speeds.get(spirit.unique_id)
        if cached is not None:
            return max(1, cached)
        return max(1, get_effective_stat(spirit, StatType.speed))

    def ensure_active_turn_begun(self) -> None:
        self._client.send({"type": MSG_SYNC_TURN})

    def submit_action(self, player_id: str, action: Dict[str, Any]) -> bool:
        if player_id != self.my_player_id:
            return False
        if not self._client.is_connected:
            raise RuntimeError("与服务器连接已断开，请重新进入联机大厅")
        self._client.send(
            {
                "type": MSG_SUBMIT_ACTION,
                "action": action,
            }
        )
        return True

    def effective_skill_energy_cost(self, actor: BattleSpirit, skill) -> int:
        from roco.core.battle.energy import skill_team_energy_cost

        return skill_team_energy_cost(actor, skill)

    def current_extra_slot(self):
        q = getattr(self.state, "extra_action_queue", None) or []
        return q[0] if q else None

    def is_my_turn(self) -> bool:
        actor_id = self.state.active_actor_id
        if not actor_id or self.state.phase != BattlePhase.waiting_for_action:
            return False
        actor = self.find_spirit_anywhere(actor_id)
        return bool(actor and actor.owner_id == self.my_player_id and actor.is_alive)
