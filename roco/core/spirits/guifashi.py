"""\u8be1\u6cd5\u5e08 \u2014 \u724c\u5e93 / \u989d\u5916\u884c\u52a8"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from ..battle.extra_action import ExtraActionSlot, ExtraActionUI, register_policy
from ..battle.types import ActionType, BattleLogType, DamageType, EffectType, StatType, BattleSpirit
from ..battle.utils import (
    apply_damage,
    apply_heal,
    calculate_damage,
    get_effective_stat,
    is_action_blocked,
    is_debuff_immune,
    make_effect,
)
from ..spirit_logic import BattleContext, DamageSource, SpiritLogic
from .guifashi_cards import (
    ALLY_TARGET_CARDS,
    CARD_SKILLS,
    ENEMY_TARGET_CARDS,
    TAROT_CARDS,
    TURN_START_DRAW,
    CardState,
    build_fate_deck,
    consume_hand_cards,
    discard_all_hand,
    draw_card,
    remove_hand_card,
    return_card_to_deck,
    transform_hand_card,
    adjust_consume_indices_after_show,
    card_label,
)

GUIFASHI_CHAIN_POLICY_ID = "guifashi_chain"


def _guifashi_chain_policy(actor: BattleSpirit, action: Dict[str, Any]) -> bool:
    """\u989d\u5916\u884c\u52a8\u4e2d\uff1a\u4e0d\u80fd\u666e\u653b/\u805a\u80fd\uff1b\u53ea\u80fd\u6253\u724c\u6280\u6216\u8df3\u8fc7\u3002"""
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


def _label(card_id: str) -> str:
    return card_label(card_id)


def _card_ids(ctx: BattleContext, spirit: BattleSpirit) -> tuple[str, str]:
    return ctx.battle_id, spirit.unique_id


def _get_cards(spirit: BattleSpirit) -> CardState:
    return CardState.from_dict(spirit.card_state)


def _save_cards(spirit: BattleSpirit, state: CardState) -> None:
    spirit.card_state = state.to_dict()


def _normalize_consume_indices(raw: Any) -> List[int]:
    if raw is None:
        return []
    if isinstance(raw, int):
        return [raw]
    return [int(i) for i in raw]


class GuifashiLogic(SpiritLogic):
    template_id = "guifashi"
    SKILLS: ClassVar[Dict[str, str]] = {
        "guifashi_draw": "_skill_draw",
        "guifashi_show": "_skill_show",
        "guifashi_cheat": "_skill_cheat",
    }

    def describe_detail_sections(self, spirit: BattleSpirit) -> list:
        """牌堆与手牌（本作为完全信息对战，双方均可见）。"""
        if not spirit.card_state:
            return []
        cs = _get_cards(spirit)
        rows = []
        for label, pile in (("牌堆", cs.deck), ("手牌", cs.hand)):
            if pile:
                cards = " ".join(f"[{i}]{_label(c)}" for i, c in enumerate(pile))
                rows.append((f"  {label} {len(pile)}  ", cards))
            else:
                rows.append((f"  {label}（空）", None))
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
        hand = _get_cards(actor).hand
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
        if spirit.template_id != "guifashi":
            return
        battle_id, spirit_id = _card_ids(ctx, spirit)
        state = CardState(deck=build_fate_deck(battle_id, spirit_id))
        _save_cards(spirit, state)

    def on_turn_start(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        if actor.template_id != "guifashi" or not actor.is_alive:
            return
        state = _get_cards(actor)
        if state.pending_moon_energy:
            state.pending_moon_energy = False
            _save_cards(actor, state)
            ctx.gain_team_energy(
                actor.owner_id,
                1,
                reason=f"{actor.name} \u7684\u6708\u4eae\u4f7f\u961f\u4f0d\u56de\u590d 1 \u70b9\u80fd\u91cf",
                log_type=BattleLogType.effect_applied,
            )
        battle_id, spirit_id = _card_ids(ctx, actor)
        for _ in range(TURN_START_DRAW):
            drawn = draw_card(state, battle_id, spirit_id)
            if not drawn:
                break
            self._log_draw(ctx, actor, drawn)
        _save_cards(actor, state)

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
        if actor.template_id != "guifashi" or not actor.is_alive:
            return
        state = _get_cards(actor)
        if not state.hand:
            return
        battle_id, spirit_id = _card_ids(ctx, actor)
        discarded = discard_all_hand(state, battle_id, spirit_id)
        _save_cards(actor, state)
        for card_id in discarded:
            self._log_discard(ctx, actor, card_id)

    def _log_draw(self, ctx: BattleContext, actor: BattleSpirit, card_id: str) -> None:
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} \u62bd\u53d6\u4e86 {_label(card_id)}",
            {"targetId": actor.unique_id, "cardId": card_id},
        )

    def _log_discard(self, ctx: BattleContext, actor: BattleSpirit, card_id: str) -> None:
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} \u5f03\u7f6e\u4e86 {_label(card_id)}",
            {"targetId": actor.unique_id, "cardId": card_id},
        )

    def _log_play(self, ctx: BattleContext, actor: BattleSpirit, card_id: str) -> None:
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} \u6253\u51fa\u4e86 {_label(card_id)}",
            {"targetId": actor.unique_id, "cardId": card_id},
        )

    def _log_consume(self, ctx: BattleContext, actor: BattleSpirit, card_id: str) -> None:
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} \u6d88\u8017\u4e86 {_label(card_id)}",
            {"targetId": actor.unique_id, "cardId": card_id},
        )

    def _log_transform(
        self, ctx: BattleContext, actor: BattleSpirit, old_id: str, new_id: str
    ) -> None:
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} \u5c06 {_label(old_id)} \u53d8\u4e3a {_label(new_id)}",
            {"targetId": actor.unique_id, "from": old_id, "to": new_id},
        )

    def can_execute_action(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        action: Dict[str, Any],
        *,
        in_extra_action: bool,
        stunned: bool,
    ) -> Optional[tuple]:
        del in_extra_action  # extra-action restrictions now live in slot policy
        at = action.get("type")
        if is_action_blocked(actor) and at == ActionType.use_skill.value:
            sk = action.get("skillId")
            if sk in CARD_SKILLS:
                return False, "\u665a\u7729\u4e2d\u65e0\u6cd5\u4f7f\u7528\u724c\u6280"

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
                [ExtraActionSlot(
                    actor_id=actor.unique_id,
                    policy_id=GUIFASHI_CHAIN_POLICY_ID,
                    source="guifashi_chain",
                )],
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
        state = _get_cards(actor)
        battle_id, spirit_id = _card_ids(ctx, actor)
        drawn = draw_card(state, battle_id, spirit_id)
        _save_cards(actor, state)
        if drawn:
            self._log_draw(ctx, actor, drawn)

    def _skill_show(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        state = _get_cards(actor)
        battle_id, spirit_id = _card_ids(ctx, actor)
        idx = int(action["cardHandIndex"])
        card = remove_hand_card(state, idx)
        return_card_to_deck(state, card, battle_id, spirit_id)
        _save_cards(actor, state)
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
        state = _get_cards(actor)
        idx = int(action["cardHandIndex"])
        new_card = action["newCardId"]
        old = transform_hand_card(state, idx, new_card)
        _save_cards(actor, state)
        self._log_transform(ctx, actor, old, new_card)

    def _append_stat_percent(
        self,
        spirit: BattleSpirit,
        source_id: str,
        *,
        effect_type: EffectType,
        stats: tuple[StatType, ...],
        value: float,
        display_name: str,
        turns: int = 1,
    ) -> None:
        for stat in stats:
            spirit.effects.append(
                make_effect(
                    effect_type,
                    source_id,
                    duration_turns=turns,
                    stat_type=stat,
                    value=value,
                    display_name=display_name,
                )
            )

    def _resolve_show_effect(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
        card: str,
    ) -> None:
        opponent_id = ctx.get_opponent_id(player_id)
        mag = get_effective_stat(actor, StatType.mag_atk)
        state = _get_cards(actor)
        battle_id, spirit_id = _card_ids(ctx, actor)
        label = _label(card)

        if card == "sun":
            actor.effects.append(
                make_effect(
                    EffectType.buff_damage_percent_boost,
                    actor.unique_id,
                    duration_turns=1,
                    value=0.24,
                    display_name=label,
                )
            )
            ctx.add_log(
                BattleLogType.effect_applied,
                f"{label}\u4f7f {actor.name} \u9020\u6210\u7684\u4f24\u5bb3\u63d0\u9ad824%\uff081\u56de\u5408\uff09\u3002",
                {"targetId": actor.unique_id},
            )
        elif card == "moon":
            if state.pending_moon_energy:
                ctx.add_log(
                    BattleLogType.effect_applied,
                    f"{label}\u6548\u679c\u5df2\u751f\u6548\uff0c\u65e0\u6cd5\u53e0\u52a0\u3002",
                    {"targetId": actor.unique_id},
                )
            else:
                ctx.advance_action(actor, 0.24)
                state.pending_moon_energy = True
                _save_cards(actor, state)
                ctx.add_log(
                    BattleLogType.effect_applied,
                    f"{label}\u4f7f {actor.name} \u4e0b\u4e00\u6b21\u884c\u52a8\u63d0\u524d24%\uff0c\u4e14\u4e0b\u56de\u5408\u5f00\u59cb\u65f6\u56de\u590d1\u70b9\u80fd\u91cf\u3002",
                    {"targetId": actor.unique_id},
                )
        elif card == "star":
            target = self._ally_target(ctx, player_id, action.get("targetId"))
            if target:
                heal = apply_heal(target, mag * 0.48)
                ctx.add_log(
                    BattleLogType.heal_applied,
                    f"{label}\u4e3a {target.name} \u56de\u590d {heal} \u70b9\u751f\u547d\uff01",
                    {"targetId": target.unique_id, "heal": heal},
                )
        elif card == "temperance":
            target = self._enemy_target(ctx, opponent_id, action.get("targetId"))
            if target and not is_debuff_immune(target):
                self._append_stat_percent(
                    target,
                    actor.unique_id,
                    effect_type=EffectType.debuff_stat_percent_reduction,
                    stats=(
                        StatType.atk,
                        StatType.mag_atk,
                        StatType.def_,
                        StatType.mag_def,
                    ),
                    value=0.09,
                    display_name=label,
                )
                ctx.add_log(
                    BattleLogType.effect_applied,
                    f"{label}\u4f7f {target.name} \u5168\u5c5e\u6027\u964d\u4f4e9%\uff081\u56de\u5408\uff09\u3002",
                    {"targetId": target.unique_id},
                )
        elif card == "judgment":
            target = self._enemy_target(ctx, opponent_id, action.get("targetId"))
            if target:
                dmg = calculate_damage(mag * 0.96, DamageType.magical, actor, target)
                actual = apply_damage(target, dmg, ctx=ctx)
                ctx.add_log(
                    BattleLogType.damage_dealt,
                    f"{label}对 {target.name} 造成了 {actual} 点魔法伤害！",
                    {"attackerId": actor.unique_id, "targetId": target.unique_id, "damage": actual},
                )
                ctx.notify_damage_taken(actor, target, actual, source=DamageSource.skill)
                if target.is_alive:
                    ctx.delay_action(target, 0.20)
                    ctx.add_log(
                        BattleLogType.effect_applied,
                        f"{label}\u4f7f {target.name} \u884c\u52a8\u5ef6\u540e20%\u3002",
                        {"targetId": target.unique_id},
                    )
        elif card == "tower":
            target = self._ally_target(ctx, player_id, action.get("targetId"))
            if target:
                self._append_stat_percent(
                    target,
                    actor.unique_id,
                    effect_type=EffectType.buff_stat_percent_boost,
                    stats=(StatType.atk, StatType.mag_atk),
                    value=0.18,
                    display_name=label,
                )
                ctx.add_log(
                    BattleLogType.effect_applied,
                    f"{label}\u4f7f {target.name} \u7269\u653b\u4e0e\u9b54\u653b\u63d0\u534718%\uff081\u56de\u5408\uff09\u3002",
                    {"targetId": target.unique_id},
                )
        elif card == "chariot":
            target = self._ally_target(ctx, player_id, action.get("targetId"))
            if target:
                self._append_stat_percent(
                    target,
                    actor.unique_id,
                    effect_type=EffectType.buff_stat_percent_boost,
                    stats=(StatType.def_, StatType.mag_def),
                    value=0.18,
                    display_name=label,
                )
                ctx.add_log(
                    BattleLogType.effect_applied,
                    f"{label}\u4f7f {target.name} \u7269\u9632\u4e0e\u9b54\u9632\u63d0\u534718%\uff081\u56de\u5408\uff09\u3002",
                    {"targetId": target.unique_id},
                )
        elif card == "hermit":
            target = self._ally_target(ctx, player_id, action.get("targetId"))
            if target:
                self._append_stat_percent(
                    target,
                    actor.unique_id,
                    effect_type=EffectType.buff_stat_percent_boost,
                    stats=(StatType.speed,),
                    value=0.18,
                    display_name=label,
                )
                ctx.add_log(
                    BattleLogType.effect_applied,
                    f"{label}\u4f7f {target.name} \u901f\u5ea6\u63d0\u534718%\uff081\u56de\u5408\uff09\u3002",
                    {"targetId": target.unique_id},
                )
        elif card == "death":
            for target in ctx.get_active_spirits(opponent_id):
                dmg = calculate_damage(mag * 0.48, DamageType.magical, actor, target)
                actual = apply_damage(target, dmg, ctx=ctx)
                ctx.add_log(
                    BattleLogType.damage_dealt,
                    f"{label}对 {target.name} 造成了 {actual} 点魔法伤害！",
                    {"attackerId": actor.unique_id, "targetId": target.unique_id, "damage": actual},
                )
                ctx.notify_damage_taken(actor, target, actual, source=DamageSource.skill)
        elif card == "fool":
            for _ in range(2):
                drawn = draw_card(state, battle_id, spirit_id)
                if not drawn:
                    break
                self._log_draw(ctx, actor, drawn)
            _save_cards(actor, state)
        elif card == "demon":
            indices = _normalize_consume_indices(action.get("consumeHandIndices"))
            if indices:
                shown_idx = int(action["cardHandIndex"])
                adjusted = adjust_consume_indices_after_show(indices, shown_idx)
                consumed = consume_hand_cards(state, adjusted)
                for card_id in consumed:
                    self._log_consume(ctx, actor, card_id)
                for _ in range(len(consumed)):
                    drawn = draw_card(state, battle_id, spirit_id)
                    if not drawn:
                        break
                    self._log_draw(ctx, actor, drawn)
            _save_cards(actor, state)

    def _validate_show(self, action: Dict[str, Any], actor: BattleSpirit) -> Optional[str]:
        state = _get_cards(actor)
        idx = action.get("cardHandIndex")
        if idx is None:
            return "\u8bf7\u9009\u62e9\u624b\u724c"
        idx = int(idx)
        if idx < 0 or idx >= len(state.hand):
            return "\u624b\u724c\u7d22\u5f15\u65e0\u6548"
        card = state.hand[idx]
        if card in ALLY_TARGET_CARDS:
            if not action.get("targetId"):
                return "\u8bf7\u9009\u62e9\u53cb\u65b9\u76ee\u6807"
        if card in ENEMY_TARGET_CARDS:
            if not action.get("targetId"):
                return "\u8bf7\u9009\u62e9\u654c\u65b9\u76ee\u6807"
        if card == "demon":
            indices = _normalize_consume_indices(action.get("consumeHandIndices"))
            if not indices:
                return "\u6076\u9b54\u9700\u9009\u62e9\u81f3\u5c11\u4e00\u5f20\u8981\u6d88\u8017\u7684\u624b\u724c"
            if len(set(indices)) != len(indices):
                return "\u6d88\u8017\u624b\u724c\u7d22\u5f15\u4e0d\u80fd\u91cd\u590d"
            for i in indices:
                if i < 0 or i >= len(state.hand) or i == idx:
                    return "\u6d88\u8017\u624b\u724c\u7d22\u5f15\u65e0\u6548"
        return None

    def _validate_cheat(self, action: Dict[str, Any], actor: BattleSpirit) -> Optional[str]:
        state = _get_cards(actor)
        idx = action.get("cardHandIndex")
        new_card = action.get("newCardId")
        if idx is None:
            return "\u8bf7\u9009\u62e9\u624b\u724c"
        idx = int(idx)
        if idx < 0 or idx >= len(state.hand):
            return "\u624b\u724c\u7d22\u5f15\u65e0\u6548"
        if not new_card or new_card not in TAROT_CARDS:
            return "\u8bf7\u6307\u5b9a\u6709\u6548\u7684\u724c\u9762"
        if new_card == state.hand[idx]:
            return "\u65b0\u724c\u4e0d\u80fd\u4e0e\u539f\u724c\u76f8\u540c"
        return None

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


guifashi_logic = GuifashiLogic()
