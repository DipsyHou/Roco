"""Shared helpers for 诡法师 card state, logs and validation."""

from __future__ import annotations

from typing import Any, List, Optional

from ..battle import messages as msg
from ..battle.types import BattleLogType, BattleSpirit
from ..spirit_logic import BattleContext
from .guifashi_cards import (
    ALLY_TARGET_CARDS,
    ENEMY_TARGET_CARDS,
    TAROT_CARDS,
    CardState,
    card_label,
)


def label(card_id: str) -> str:
    return card_label(card_id)


def card_ids(ctx: BattleContext, spirit: BattleSpirit) -> tuple[str, str]:
    return ctx.battle_id, spirit.unique_id


def get_cards(spirit: BattleSpirit) -> CardState:
    return CardState.from_dict(spirit.card_state)


def save_cards(spirit: BattleSpirit, state: CardState) -> None:
    spirit.card_state = state.to_dict()


def normalize_consume_indices(raw: Any) -> List[int]:
    if raw is None:
        return []
    if isinstance(raw, int):
        return [raw]
    return [int(i) for i in raw]


class GuifashiLogMixin:
    def _log_draw(self, ctx: BattleContext, actor: BattleSpirit, card_id: str) -> None:
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.drew_card(actor.name, label(card_id)),
            {"targetId": actor.unique_id, "cardId": card_id},
        )

    def _log_discard(self, ctx: BattleContext, actor: BattleSpirit, card_id: str) -> None:
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.discarded_card(actor.name, label(card_id)),
            {"targetId": actor.unique_id, "cardId": card_id},
        )

    def _log_play(self, ctx: BattleContext, actor: BattleSpirit, card_id: str) -> None:
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.played_card(actor.name, label(card_id)),
            {"targetId": actor.unique_id, "cardId": card_id},
        )

    def _log_consume(self, ctx: BattleContext, actor: BattleSpirit, card_id: str) -> None:
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.consumed_card(actor.name, label(card_id)),
            {"targetId": actor.unique_id, "cardId": card_id},
        )

    def _log_transform(
        self, ctx: BattleContext, actor: BattleSpirit, old_id: str, new_id: str
    ) -> None:
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.transformed_card(actor.name, label(old_id), label(new_id)),
            {"targetId": actor.unique_id, "from": old_id, "to": new_id},
        )


class GuifashiTargetMixin:
    def _ally_target(
        self,
        ctx: BattleContext,
        player_id: str,
        target_id: Optional[str],
    ) -> Optional[BattleSpirit]:
        if not target_id:
            return None
        target = ctx.find_spirit_anywhere(target_id)
        if not target or not target.is_alive or target.owner_id != player_id:
            return None
        return target

    def _enemy_target(
        self,
        ctx: BattleContext,
        opponent_id: str,
        target_id: Optional[str],
    ) -> Optional[BattleSpirit]:
        if not target_id:
            return None
        target = ctx.find_spirit_anywhere(target_id)
        if not target or not target.is_alive or target.owner_id != opponent_id:
            return None
        return target


class GuifashiValidationMixin:
    def _validate_show(self, action: dict[str, Any], actor: BattleSpirit) -> Optional[str]:
        state = get_cards(actor)
        idx = action.get("cardHandIndex")
        if idx is None:
            return "请选择手牌"
        idx = int(idx)
        if idx < 0 or idx >= len(state.hand):
            return "手牌索引无效"
        card = state.hand[idx]
        if card in ALLY_TARGET_CARDS and not action.get("targetId"):
            return "请选择友方目标"
        if card in ENEMY_TARGET_CARDS and not action.get("targetId"):
            return "请选择敌方目标"
        if card == "demon":
            indices = normalize_consume_indices(action.get("consumeHandIndices"))
            if not indices:
                return "恶魔需选择至少一张要消耗的手牌"
            if len(set(indices)) != len(indices):
                return "消耗手牌索引不能重复"
            for i in indices:
                if i < 0 or i >= len(state.hand) or i == idx:
                    return "消耗手牌索引无效"
        return None

    def _validate_cheat(self, action: dict[str, Any], actor: BattleSpirit) -> Optional[str]:
        state = get_cards(actor)
        idx = action.get("cardHandIndex")
        new_card = action.get("newCardId")
        if idx is None:
            return "请选择手牌"
        idx = int(idx)
        if idx < 0 or idx >= len(state.hand):
            return "手牌索引无效"
        if not new_card or new_card not in TAROT_CARDS:
            return "请指定有效的牌面"
        if new_card == state.hand[idx]:
            return "新牌不能与原牌相同"
        return None
