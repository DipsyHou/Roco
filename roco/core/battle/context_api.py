"""BattleContext-facing API shared by battle systems and spirit logic.

This mixin exposes battle state lookup, logging, and damage hooks to spirit
logic and other battle subsystems. It should remain a thin API surface rather
than a turn-orchestration layer.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from .actions import ActionDict
from .events import (
    DamageEvent,
    DamageSource,
    EffectAppliedEvent,
    dispatch_damage,
    dispatch_effect_applied,
)
from .formation import living_slot_neighbors
from .effect_meta import effect_category
from .types import (
    BattleLogEntry,
    BattleLogType,
    BattlePresentationEvent,
    BattleSpirit,
    EffectType,
)
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
        log_index = len(self.state.battle_log)
        self.state.battle_log.append(
            BattleLogEntry(
                type=log_type,
                turn=self.state.action_count,
                message=message,
                data=data,
            )
        )
        payload = data or {}
        target_id = payload.get("targetId")
        amount = 0
        kind = "log"
        effect_kind = None
        if log_type == BattleLogType.damage_dealt:
            kind = "damage"
            amount = int(payload.get("damage") or 0)
        elif log_type == BattleLogType.heal_applied or "heal" in payload:
            kind = "heal"
            amount = int(payload.get("heal") or 0)
        elif log_type == BattleLogType.effect_applied:
            kind = "effect_applied"
            effect_kind = self._presentation_effect_kind(target_id, payload)
        elif log_type == BattleLogType.effect_removed:
            kind = "effect_removed"
        elif log_type == BattleLogType.passive_triggered:
            kind = "passive"
        elif log_type == BattleLogType.spirit_defeated:
            kind = "defeat"
        target = self.find_spirit_anywhere(str(target_id or ""))
        self.state.presentation_events.append(
            BattlePresentationEvent(
                sequence=len(self.state.presentation_events),
                log_index=log_index,
                kind=kind,
                target_id=str(target_id) if target_id else None,
                amount=amount,
                effect_kind=effect_kind,
                current_hp=(int(target.current_hp) if target else None),
                max_hp=(int(target.max_hp) if target else None),
                effects=(tuple(copy.deepcopy(target.effects)) if target else ()),
                charge=(float(target.charge) if target else None),
            )
        )
        if log_type == BattleLogType.effect_applied and target:
            effect = self._logged_effect(target, payload)
            if effect is not None:
                raw_prior_types = payload.get("priorEffectTypes")
                if isinstance(raw_prior_types, (list, tuple, set, frozenset)):
                    prior_effect_types = frozenset(
                        effect_type
                        for raw_type in raw_prior_types
                        if (effect_type := self._parse_effect_type(raw_type)) is not None
                    )
                else:
                    prior_effect_types = frozenset(
                        current.type for current in target.effects
                    )
                dispatch_effect_applied(
                    self,
                    EffectAppliedEvent(
                        source=self.find_spirit_anywhere(effect.source_id),
                        target=target,
                        effect_type=effect.type,
                        effect_id=effect.id,
                        prior_effect_types=prior_effect_types,
                    ),
                )

    @staticmethod
    def _parse_effect_type(raw_type: Any) -> Optional[EffectType]:
        try:
            return EffectType(raw_type)
        except (TypeError, ValueError):
            return None

    def _logged_effect(self, target: BattleSpirit, payload: Dict[str, Any]):
        effect_id = payload.get("effectId")
        if effect_id:
            return next((e for e in target.effects if e.id == effect_id), None)
        source_id = payload.get("sourceId")
        raw_type = payload.get("effectType")
        for effect in reversed(target.effects):
            if source_id is not None and effect.source_id != source_id:
                continue
            if raw_type is not None and effect.type.value != raw_type:
                continue
            return effect
        return None

    def _presentation_effect_kind(
        self, target_id: Optional[str], payload: Dict[str, Any]
    ) -> str:
        raw_type = payload.get("effectType")
        if raw_type:
            try:
                return effect_category(EffectType(raw_type))
            except (TypeError, ValueError):
                pass
        target = self.find_spirit_anywhere(str(target_id or ""))
        if target and target.effects:
            effect_id = payload.get("effectId")
            effect = next(
                (item for item in reversed(target.effects) if item.id == effect_id),
                target.effects[-1],
            )
            return effect_category(effect.type)
        return "state"

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
        dot_kind: Optional[str] = None,
    ) -> None:
        dispatch_damage(
            self,
            DamageEvent(
                attacker=attacker,
                target=target,
                damage=damage,
                source=source,
                dot_kind=dot_kind,
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
