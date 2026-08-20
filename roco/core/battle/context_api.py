"""BattleContext-facing API shared by battle systems and spirit logic.

This mixin exposes battle state lookup, logging, and damage hooks to spirit
logic and other battle subsystems. It should remain a thin API surface rather
than a turn-orchestration layer.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .actions import ActionDict
from .events import DamageEvent, DamageSource, dispatch_damage
from .formation import living_slot_neighbors
from .types import BattleLogEntry, BattleLogType, BattleSpirit
from . import messages as msg


class BattleContextMixin:
    @property
    def battle_id(self) -> str:
        return self.state.battle_id

    @property
    def player_ids(self) -> List[str]:
        """Public, ordered [player1_id, player2_id]."""
        return list(self._player_ids)

    def next_rng(self, domain: str, *parts: Any):
        """Deterministic per-domain RNG for one random draw (see rng.py)."""
        return self._rng.next(domain, *parts)

    def get_opponent_id(self, player_id: str) -> str:
        return next(pid for pid in self._player_ids if pid != player_id)

    def find_spirit(self, player_id: str, unique_id: str) -> Optional[BattleSpirit]:
        pd = self.state.players.get(player_id)
        if not pd:
            return None
        return next((s for s in pd.spirits if s.unique_id == unique_id), None)

    def find_spirit_anywhere(self, unique_id: str) -> Optional[BattleSpirit]:
        for pid in self._player_ids:
            s = self.find_spirit(pid, unique_id)
            if s:
                return s
        return None

    def get_active_spirits(self, player_id: str) -> List[BattleSpirit]:
        pd = self.state.players.get(player_id)
        if not pd:
            return []
        return [s for s in pd.spirits if s.is_alive]

    def get_all_spirits(self, player_id: str) -> List[BattleSpirit]:
        pd = self.state.players.get(player_id)
        return pd.spirits if pd else []

    def get_adjacent_enemies(self, target: BattleSpirit) -> List[BattleSpirit]:
        """同阵营按槽位排序后的左右邻（仅存活；中间阵亡不挡扩散）。"""
        return living_slot_neighbors(self.get_active_spirits(target.owner_id), target)

    def get_adjacent_allies(
        self, anchor: BattleSpirit, player_id: str
    ) -> List[BattleSpirit]:
        """锚点精灵及其左右邻己方场上精灵（仅存活；中间阵亡不挡）。"""
        return [anchor] + living_slot_neighbors(
            self.get_active_spirits(player_id), anchor
        )

    def add_log(
        self,
        log_type: BattleLogType,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.state.battle_log.append(
            BattleLogEntry(
                type=log_type,
                turn=self.state.action_count,
                message=message,
                data=data,
            )
        )

    def execute_normal_attack(
        self,
        player_id: str,
        action: ActionDict,
        is_auto_triggered: bool = False,
    ) -> None:
        self._actions.execute_normal_attack_impl(player_id, action, is_auto_triggered)

    def notify_damage_taken(
        self,
        attacker: Optional[BattleSpirit],
        target: BattleSpirit,
        damage: int,
        *,
        source: DamageSource = DamageSource.other,
    ) -> None:
        dispatch_damage(
            self,
            DamageEvent(
                attacker=attacker,
                target=target,
                damage=damage,
                source=source,
            ),
        )

    def log_effect_expired(self, spirit: BattleSpirit, eff) -> None:
        self.add_log(
            BattleLogType.effect_removed,
            msg.effect_expired(spirit.name),
            {"targetId": spirit.unique_id, "effectId": eff.id},
        )

    def execute_action(self, player_id: str, action: ActionDict) -> None:
        self._actions.execute_action(player_id, action)
