"""梦想龙 — 技能 & 被动"""

from __future__ import annotations

from typing import Any, ClassVar, Dict

from ..battle import messages as msg
from ..battle.types import BattleLogType, EffectType, StatType, BattleSpirit
from ..battle.utils import (
    is_debuff_effect,
    is_debuff_immune,
    make_effect,
)
from ._combat import deal_atk_ratio
from ..spirit_logic import BattleContext, DamageSource, SpiritLogic

STAT_NAMES = {
    "atk": "物攻",
    "magAtk": "魔攻",
    "def": "物防",
    "magDef": "魔防",
    "speed": "速度",
}


class ChaoslingLogic(SpiritLogic):
    template_id = "chaosling"
    SKILLS: ClassVar[Dict[str, str]] = {
        "chaosling_skill1": "_skill_rage",
        "chaosling_skill2": "_skill_storm",
        "chaosling_skill3": "_skill_reverse",
    }

    def on_turn_end(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
        *,
        stunned: bool = False,
    ) -> None:
        del player_id, action
        if stunned or actor.template_id != "chaosling" or not actor.is_alive:
            return
        self._trigger_chaos_passive(ctx, actor)

    def on_turn_start(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        self._process_channeling(ctx, actor)

    def get_damage_reduction(self, spirit: BattleSpirit) -> float:
        debuff_count = sum(1 for e in spirit.effects if is_debuff_effect(e.type))
        return min(0.1, debuff_count * 0.02)

    def _trigger_chaos_passive(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        stats = [
            StatType.atk,
            StatType.mag_atk,
            StatType.def_,
            StatType.mag_def,
            StatType.speed,
        ]
        rng = ctx.next_rng("chaosling_tide", actor.unique_id)
        positive_stat = rng.choice(stats)
        actor.effects.append(
            make_effect(
                EffectType.buff_stat_percent_boost,
                actor.unique_id,
                stat_type=positive_stat,
                value=0.1,
                display_name="梦想潮汐",
            )
        )
        negative_stat = rng.choice(stats)
        if not is_debuff_immune(actor):
            actor.effects.append(
                make_effect(
                    EffectType.debuff_stat_percent_reduction,
                    actor.unique_id,
                    stat_type=negative_stat,
                    value=0.1,
                    display_name="梦想潮汐",
                )
            )
        pos = STAT_NAMES.get(positive_stat.value, "?")
        neg = STAT_NAMES.get(negative_stat.value, "?")
        ctx.add_log(
            BattleLogType.passive_triggered,
            msg.passive(actor.name, "梦想潮汐"),
            msg.data_effect(actor.unique_id, actor.unique_id),
        )

    def _process_channeling(self, ctx: BattleContext, spirit: BattleSpirit) -> None:
        channeling = next(
            (e for e in spirit.effects if e.type == EffectType.state_channeling_skill),
            None,
        )
        if not channeling or channeling.channel_skill_id != "chaosling_skill1":
            return
        phase = channeling.channel_phase or 1
        if phase == 1:
            spirit.effects.append(
                make_effect(
                    EffectType.buff_stat_percent_boost,
                    spirit.unique_id,
                    stat_type=StatType.atk,
                    value=0.1,
                    display_name="愿力凝聚",
                )
            )
            if not is_debuff_immune(spirit):
                spirit.effects.append(
                    make_effect(
                        EffectType.debuff_stat_percent_reduction,
                        spirit.unique_id,
                        stat_type=StatType.def_,
                        value=0.1,
                        display_name="愿力凝聚",
                    )
                )
            ctx.add_log(
                BattleLogType.effect_applied,
                msg.effect_gained(spirit.name, "愿力凝聚"),
                msg.data_effect(spirit.unique_id, spirit.unique_id),
            )
            channeling.channel_phase = 2
        elif phase == 2:
            spirit.effects.append(
                make_effect(
                    EffectType.buff_stat_percent_boost,
                    spirit.unique_id,
                    stat_type=StatType.atk,
                    value=0.1,
                    display_name="愿力凝聚",
                )
            )
            if not is_debuff_immune(spirit):
                spirit.effects.append(
                    make_effect(
                        EffectType.debuff_stat_percent_reduction,
                        spirit.unique_id,
                        stat_type=StatType.mag_def,
                        value=0.1,
                        display_name="愿力凝聚",
                    )
                )
            ctx.add_log(
                BattleLogType.effect_applied,
                msg.effect_gained(spirit.name, "愿力凝聚"),
                msg.data_effect(spirit.unique_id, spirit.unique_id),
            )
            spirit.effects = [
                e for e in spirit.effects if e.type != EffectType.state_channeling_skill
            ]

    def _skill_rage(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id, action
        actor.effects = [
            e for e in actor.effects if e.type != EffectType.state_channeling_skill
        ]
        actor.effects.append(
            make_effect(
                EffectType.buff_stat_percent_boost,
                actor.unique_id,
                stat_type=StatType.atk,
                value=0.1,
                display_name="愿力凝聚",
            )
        )
        if not is_debuff_immune(actor):
            actor.effects.append(
                make_effect(
                    EffectType.debuff_stat_percent_reduction,
                    actor.unique_id,
                    stat_type=StatType.mag_atk,
                    value=0.1,
                    display_name="愿力凝聚",
                )
            )
        actor.effects.append(
            make_effect(
                EffectType.state_channeling_skill,
                actor.unique_id,
                duration_turns=3,
                channel_phase=1,
                channel_skill_id="chaosling_skill1",
                display_name="愿力凝聚",
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.effect_gained(actor.name, "愿力凝聚"),
            msg.data_effect(actor.unique_id, actor.unique_id),
        )

    def _skill_storm(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del action
        opponent_id = ctx.get_opponent_id(player_id)
        for target in ctx.get_active_spirits(opponent_id):
            deal_atk_ratio(
                ctx,
                actor,
                target,
                0.6,
                lambda a, t=target: msg.skill_damage(
                    actor.name, "精神风暴", t.name, a
                ),
                source=DamageSource.skill,
            )

    def _skill_reverse(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        opponent_id = ctx.get_opponent_id(player_id)
        for eff in actor.effects:
            if eff.type == EffectType.debuff_stat_percent_reduction and eff.value is not None:
                eff.type = EffectType.buff_stat_percent_boost
                eff.display_name = "命运逆转"
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.effect_gained(actor.name, "命运逆转"),
            msg.data_effect(actor.unique_id, actor.unique_id),
        )
        tid = action.get("targetId")
        if not tid:
            return
        target = ctx.find_spirit_anywhere(tid)
        if target and target.is_alive and target.owner_id == opponent_id:
            deal_atk_ratio(
                ctx,
                actor,
                target,
                1.5,
                lambda a: msg.skill_damage(actor.name, "命运逆转", target.name, a),
                source=DamageSource.skill,
            )


chaosling_logic = ChaoslingLogic()
