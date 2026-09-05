"""诡法师「揭晓」牌面效果解析。"""

from __future__ import annotations

from typing import Any

from ..battle import messages as msg
from ..battle.types import BattleLogType, BattleSpirit, DamageType, EffectType, StatType
from ..battle.utils import (
    apply_damage,
    apply_heal,
    calculate_damage,
    get_effective_stat,
    is_debuff_immune,
    make_effect,
)
from ..spirit_logic import BattleContext, DamageSource
from .guifashi_cards import (
    adjust_consume_indices_after_show,
    consume_hand_cards,
    draw_card,
)
from .guifashi_support import card_ids, get_cards, label, normalize_consume_indices, save_cards


class GuifashiShowEffectsMixin:
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
        action: dict[str, Any],
        card: str,
    ) -> None:
        opponent_id = ctx.get_opponent_id(player_id)
        mag = get_effective_stat(actor, StatType.mag_atk)
        state = get_cards(actor)
        battle_id, spirit_id = card_ids(ctx, actor)
        card_name = label(card)

        if card == "sun":
            actor.effects.append(
                make_effect(
                    EffectType.buff_damage_percent_boost,
                    actor.unique_id,
                    duration_turns=1,
                    value=0.24,
                    display_name=card_name,
                )
            )
            ctx.add_log(
                BattleLogType.effect_applied,
                msg.effect_gained(actor.name, card_name),
                {"targetId": actor.unique_id},
            )
        elif card == "moon":
            if state.pending_moon_energy:
                ctx.add_log(
                    BattleLogType.effect_applied,
                    msg.effect_blocked(card_name),
                    {"targetId": actor.unique_id},
                )
            else:
                ctx.advance_action(actor, 0.24)
                state.pending_moon_energy = True
                save_cards(actor, state)
                ctx.add_log(
                    BattleLogType.effect_applied,
                    msg.effect_gained(actor.name, card_name),
                    {"targetId": actor.unique_id},
                )
        elif card == "star":
            target = self._ally_target(ctx, player_id, action.get("targetId"))
            if target:
                heal = apply_heal(target, mag * 0.48)
                ctx.add_log(
                    BattleLogType.heal_applied,
                    msg.heal(card_name, target.name, heal),
                    msg.data_heal(actor.unique_id, target.unique_id, heal),
                )
        elif card == "temperance":
            target = self._enemy_target(ctx, opponent_id, action.get("targetId"))
            if target and not is_debuff_immune(target):
                self._append_stat_percent(
                    target,
                    actor.unique_id,
                    effect_type=EffectType.debuff_stat_percent_reduction,
                    stats=(StatType.atk, StatType.mag_atk, StatType.def_, StatType.mag_def),
                    value=0.09,
                    display_name=card_name,
                )
                ctx.add_log(
                    BattleLogType.effect_applied,
                    msg.effect_gained(target.name, card_name),
                    {"targetId": target.unique_id},
                )
        elif card == "judgment":
            target = self._enemy_target(ctx, opponent_id, action.get("targetId"))
            if target:
                actual = self._deal_card_magic(ctx, actor, target, mag * 0.96, card_name)
                if actual > 0 and target.is_alive:
                    ctx.delay_action(target, 0.20)
                    ctx.add_log(
                        BattleLogType.effect_applied,
                        msg.effect_gained(target.name, card_name),
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
                    display_name=card_name,
                )
                ctx.add_log(
                    BattleLogType.effect_applied,
                    msg.effect_gained(target.name, card_name),
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
                    display_name=card_name,
                )
                ctx.add_log(
                    BattleLogType.effect_applied,
                    msg.effect_gained(target.name, card_name),
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
                    display_name=card_name,
                )
                ctx.add_log(
                    BattleLogType.effect_applied,
                    msg.effect_gained(target.name, card_name),
                    {"targetId": target.unique_id},
                )
        elif card == "death":
            for target in ctx.get_active_spirits(opponent_id):
                self._deal_card_magic(ctx, actor, target, mag * 0.48, card_name)
        elif card == "fool":
            for _ in range(2):
                drawn = draw_card(state, battle_id, spirit_id)
                if not drawn:
                    break
                self._log_draw(ctx, actor, drawn)
            save_cards(actor, state)
        elif card == "demon":
            indices = normalize_consume_indices(action.get("consumeHandIndices"))
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
            save_cards(actor, state)

    def _deal_card_magic(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        target: BattleSpirit,
        raw: float,
        card_name: str,
    ) -> int:
        dmg = calculate_damage(raw, DamageType.magical, actor, target)
        actual = apply_damage(target, dmg, ctx=ctx)
        ctx.add_log(
            BattleLogType.damage_dealt,
            msg.damage(card_name, target.name, actual, kind=msg.KIND_MAGICAL),
            msg.data_damage(actor.unique_id, target.unique_id, actual),
        )
        ctx.notify_damage_taken(actor, target, actual, source=DamageSource.skill)
        return actual
