"""上古战龙 — 守护者 / 龙之舞 / 传说力量 / 过肩摔"""

from __future__ import annotations

from typing import Any, ClassVar, Dict

from ..battle import messages as msg
from ..battle.types import BattleLogType, BattleSpirit, DamageType, EffectType, StatType
from ..battle.utils import get_effective_stat, make_effect
from ._combat import deal_damage, target_enemy
from ..spirit_logic import BattleContext, DamageEvent, DamageSource, SpiritLogic

GUARDIAN_DEF_BONUS = 0.15
GUARDIAN_DURATION = 2
LEGENDARY_ATK_RATIO = 0.50
LEGENDARY_HP_RATIO = 0.10
THROW_ATK_RATIO = 1.20


class ClawdragonLogic(SpiritLogic):
    template_id = "clawdragon"
    SKILLS: ClassVar[Dict[str, str]] = {
        "clawdragon_skill1": "_skill_legendary_power",
        "clawdragon_skill2": "_skill_dragon_dance",
        "clawdragon_skill3": "_skill_shoulder_throw",
    }

    def on_turn_start(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        if actor.template_id != self.template_id:
            return
        actor._guardian_passive_used = False

    def on_damage(self, ctx: BattleContext, spirit: BattleSpirit, event: DamageEvent) -> None:
        if spirit.template_id != self.template_id:
            return
        target = event.target
        if target.template_id != self.template_id or not target.is_alive:
            return
        if event.damage <= 0 or getattr(target, "_guardian_passive_used", False):
            return
        target._guardian_passive_used = True
        target.effects.append(
            make_effect(
                EffectType.buff_stat_percent_boost,
                target.unique_id,
                stat_type=StatType.def_,
                value=GUARDIAN_DEF_BONUS,
                duration_turns=GUARDIAN_DURATION,
                display_name="守护者",
            )
        )
        target.effects.append(
            make_effect(
                EffectType.buff_stat_percent_boost,
                target.unique_id,
                stat_type=StatType.mag_def,
                value=GUARDIAN_DEF_BONUS,
                duration_turns=GUARDIAN_DURATION,
                display_name="守护者",
            )
        )
        ctx.add_log(
            BattleLogType.passive_triggered,
            msg.passive(target.name, "守护者"),
            msg.data_effect(target.unique_id, target.unique_id),
        )

    def _skill_legendary_power(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        atk = get_effective_stat(actor, StatType.atk)
        raw = atk * LEGENDARY_ATK_RATIO + target.current_hp * LEGENDARY_HP_RATIO
        deal_damage(
            ctx,
            actor,
            target,
            raw,
            DamageType.physical,
            lambda a: msg.skill_damage(actor.name, "传说力量", target.name, a),
            source=DamageSource.skill,
        )

    def _skill_dragon_dance(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id, action
        actor.effects.append(
            make_effect(
                EffectType.buff_stat_percent_boost,
                actor.unique_id,
                stat_type=StatType.atk,
                value=0.20,
                display_name="龙之舞",
            )
        )
        actor.effects.append(
            make_effect(
                EffectType.buff_stat_percent_boost,
                actor.unique_id,
                stat_type=StatType.speed,
                value=0.20,
                display_name="龙之舞",
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.effect_gained(actor.name, "龙之舞"),
            msg.data_effect(actor.unique_id, actor.unique_id),
        )

    def _skill_shoulder_throw(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        atk = get_effective_stat(actor, StatType.atk)
        deal_damage(
            ctx,
            actor,
            target,
            atk * THROW_ATK_RATIO,
            DamageType.physical,
            lambda a: msg.skill_damage(actor.name, "过肩摔", target.name, a),
            source=DamageSource.skill,
        )
        if target.is_alive:
            target.effects.append(
                make_effect(EffectType.debuff_stun, actor.unique_id, duration_turns=1)
            )
            ctx.add_log(
                BattleLogType.effect_applied,
                msg.effect_gained(target.name, "眩晕"),
                msg.data_effect(target.unique_id, actor.unique_id),
            )


clawdragon_logic = ClawdragonLogic()
