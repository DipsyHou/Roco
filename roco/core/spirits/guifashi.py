"""诡法师 — 牌库 / 额外行动"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from ..battle.extra_action import ExtraActionSlot, ExtraActionUI, register_policy
from ..battle.types import ActionType, BattleLogType, BattleSpirit
from ..battle.utils import is_action_blocked
from ..spirit_logic import BattleContext, SpiritLogic
from .guifashi_cards import (
    CARD_SKILLS,
    TURN_START_DRAW,
    build_fate_deck,
    discard_all_hand,
    draw_card,
    remove_hand_card,
    return_card_to_deck,
    transform_hand_card,
)
from .guifashi_effects import GuifashiShowEffectsMixin
from .guifashi_support import (
    GuifashiLogMixin,
    GuifashiTargetMixin,
    GuifashiValidationMixin,
    card_ids,
    get_cards,
    label,
    save_cards,
)

GUIFASHI_CHAIN_POLICY_ID = "guifashi_chain"
TEMPLATE_ID = "guifashi"


def _guifashi_chain_policy(actor: BattleSpirit, action: Dict[str, Any]) -> bool:
    """额外行动中：不能普攻/聚能；只能打牌技或跳过。"""
    at = action.get("type")
    if at == ActionType.skip.value:
        return True
    if at == ActionType.use_skill.value:
        return action.get("skillId") in CARD_SKILLS
    return False


register_policy(
    GUIFASHI_CHAIN_POLICY_ID,
    _guifashi_chain_policy,
    ExtraActionUI(
        hint="（额外行动中：占卜/揭晓/逆位 或 跳过收束）",
        allow_normal_attack=False,
        allow_gather=False,
        allow_skip=True,
    ),
)


class GuifashiLogic(
    GuifashiLogMixin,
    GuifashiTargetMixin,
    GuifashiValidationMixin,
    GuifashiShowEffectsMixin,
    SpiritLogic,
):
    template_id = TEMPLATE_ID
    SKILLS: ClassVar[Dict[str, str]] = {
        "guifashi_draw": "_skill_draw",
        "guifashi_show": "_skill_show",
        "guifashi_cheat": "_skill_cheat",
    }

    def describe_detail_sections(self, spirit: BattleSpirit) -> list:
        """牌堆与手牌（本作为完全信息对战，双方均可见）。"""
        if not spirit.card_state:
            return []
        cs = get_cards(spirit)
        rows = []
        for pile_name, pile in (("牌堆", cs.deck), ("手牌", cs.hand)):
            if pile:
                cards = " ".join(f"[{i}]{label(c)}" for i, c in enumerate(pile))
                rows.append((f"  {pile_name} {len(pile)}  ", cards))
            else:
                rows.append((f"  {pile_name}（空）", None))
        return [("塔罗", rows)]

    def get_attack_launch_targets(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        action: Dict[str, Any],
        skill,
    ) -> Optional[List[BattleSpirit]]:
        """揭晓：仅审判 / 死神有伤害倍率，算发动攻击；其余牌面不算。"""
        if getattr(skill, "id", None) != "guifashi_show":
            return None
        raw_idx = action.get("cardHandIndex")
        if raw_idx is None:
            return []
        try:
            idx = int(raw_idx)
        except (TypeError, ValueError):
            return []
        hand = get_cards(actor).hand
        if idx < 0 or idx >= len(hand):
            return []
        card = hand[idx]
        opponent_id = ctx.get_opponent_id(actor.owner_id)
        if card == "judgment":
            target = self._enemy_target(ctx, opponent_id, action.get("targetId"))
            return [target] if target else []
        if card == "death":
            return [s for s in ctx.get_active_spirits(opponent_id) if s.is_alive]
        return []

    def on_battle_start(self, ctx: BattleContext, spirit: BattleSpirit) -> None:
        if spirit.template_id != TEMPLATE_ID:
            return
        battle_id, spirit_id = card_ids(ctx, spirit)
        state = get_cards(spirit)
        state.deck = build_fate_deck(battle_id, spirit_id)
        save_cards(spirit, state)

    def on_turn_start(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        if actor.template_id != TEMPLATE_ID or not actor.is_alive:
            return
        state = get_cards(actor)
        if state.pending_moon_energy:
            state.pending_moon_energy = False
            save_cards(actor, state)
            ctx.gain_team_energy(
                actor.owner_id,
                1,
                reason=f"{actor.name} 的月亮使队伍回复 1 点能量",
                log_type=BattleLogType.effect_applied,
            )
        battle_id, spirit_id = card_ids(ctx, actor)
        for _ in range(TURN_START_DRAW):
            drawn = draw_card(state, battle_id, spirit_id)
            if not drawn:
                break
            self._log_draw(ctx, actor, drawn)
        save_cards(actor, state)

    def on_turn_end(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
        *,
        stunned: bool = False,
    ) -> None:
        del player_id, action, stunned
        if actor.template_id != TEMPLATE_ID or not actor.is_alive:
            return
        state = get_cards(actor)
        if not state.hand:
            return
        battle_id, spirit_id = card_ids(ctx, actor)
        discarded = discard_all_hand(state, battle_id, spirit_id)
        save_cards(actor, state)
        for card_id in discarded:
            self._log_discard(ctx, actor, card_id)

    def can_execute_action(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        action: Dict[str, Any],
        *,
        in_extra_action: bool,
        stunned: bool,
    ) -> Optional[tuple]:
        del ctx, in_extra_action, stunned  # extra-action restrictions now live in slot policy
        at = action.get("type")
        if is_action_blocked(actor) and at == ActionType.use_skill.value:
            sk = action.get("skillId")
            if sk in CARD_SKILLS:
                return False, "眩晕中无法使用牌技"

        if at == ActionType.use_skill.value:
            sk = action.get("skillId")
            if sk == "guifashi_show":
                err = self._validate_show(action, actor)
                if err:
                    return False, err
            elif sk == "guifashi_cheat":
                err = self._validate_cheat(action, actor)
                if err:
                    return False, err
        return None

    def execute_skill(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        sk = action.get("skillId") or ""
        name = type(self).SKILLS.get(sk)
        if not name:
            return
        getattr(self, name)(ctx, player_id, actor, action)
        # 牌技连锁：紧跟着插一次额外行动（仅牌技 + 跳过）
        if sk in CARD_SKILLS:
            ctx.queue_extra_actions(
                [
                    ExtraActionSlot(
                        actor_id=actor.unique_id,
                        policy_id=GUIFASHI_CHAIN_POLICY_ID,
                        source="guifashi_chain",
                    )
                ],
                front=True,
            )

    def _skill_draw(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id, action
        state = get_cards(actor)
        battle_id, spirit_id = card_ids(ctx, actor)
        drawn = draw_card(state, battle_id, spirit_id)
        save_cards(actor, state)
        if drawn:
            self._log_draw(ctx, actor, drawn)

    def _skill_show(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        state = get_cards(actor)
        battle_id, spirit_id = card_ids(ctx, actor)
        idx = int(action["cardHandIndex"])
        card = remove_hand_card(state, idx)
        return_card_to_deck(state, card, battle_id, spirit_id)
        save_cards(actor, state)
        self._log_play(ctx, actor, card)
        self._resolve_show_effect(ctx, player_id, actor, action, card)

    def _skill_cheat(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id
        state = get_cards(actor)
        idx = int(action["cardHandIndex"])
        new_card = action["newCardId"]
        old = transform_hand_card(state, idx, new_card)
        save_cards(actor, state)
        self._log_transform(ctx, actor, old, new_card)


guifashi_logic = GuifashiLogic()
