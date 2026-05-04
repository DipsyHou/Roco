"""混沌灵 — 技能 & 被动"""

from __future__ import annotations

import random
from typing import Any, Dict

from ..battle_types import BattleLogType, DamageType, EffectType, StatType, BattleSpirit
from ..battle_utils import (
    apply_damage,
    calculate_damage,
    consume_next_damage_reduction,
    get_effective_stat,
    is_debuff_immune,
    make_effect,
)
from ..spirit_logic import BattleContext, SpiritLogic

STAT_NAMES = {
    "atk": "物攻",
    "magAtk": "魔攻",
    "def": "物防",
    "magDef": "魔防",
    "speed": "速度",
}


class ChaoslingLogic(SpiritLogic):
    template_id = "chaosling"

    def execute_skill(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        opponent_id = ctx.get_opponent_id(player_id)
        sk = action.get("skillId")
        if sk == "chaosling_skill1":
            self._skill_rage(ctx, actor)
        elif sk == "chaosling_skill2":
            self._skill_storm(ctx, actor, opponent_id)
        elif sk == "chaosling_skill3":
            self._skill_reverse(ctx, actor, action, opponent_id)

    def on_after_normal_attack(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        is_auto_triggered: bool,
    ) -> None:
        if not is_auto_triggered:
            self._trigger_chaos_passive(ctx, actor)

    def on_after_skill(self, ctx: BattleContext, player_id: str, actor: BattleSpirit) -> None:
        self._trigger_chaos_passive(ctx, actor)

    def on_end_of_turn(self, ctx: BattleContext, spirit: BattleSpirit) -> None:
        self._process_channeling(ctx, spirit)

    def _trigger_chaos_passive(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        if actor.template_id != "chaosling" or not actor.is_alive:
            return
        stats = [
            StatType.atk,
            StatType.mag_atk,
            StatType.def_,
            StatType.mag_def,
            StatType.speed,
        ]
        positive_stat = random.choice(stats)
        actor.effects.append(
            make_effect(
                EffectType.stat_percent_modify,
                actor.unique_id,
                remaining_turns=999,
                is_debuff=False,
                stat_type=positive_stat,
                value=0.1,
            )
        )
        negative_stat = random.choice(stats)
        if not is_debuff_immune(actor):
            actor.effects.append(
                make_effect(
                    EffectType.stat_percent_modify,
                    actor.unique_id,
                    remaining_turns=999,
                    is_debuff=True,
                    stat_type=negative_stat,
                    value=-0.1,
                )
            )
        ctx.add_log(
            BattleLogType.passive_triggered,
            f"{actor.name} 的混沌波动：{STAT_NAMES.get(positive_stat.value, '?')}提升10%，"
            f"{STAT_NAMES.get(negative_stat.value, '?')}降低10%！",
            {"targetId": actor.unique_id},
        )

    def _process_channeling(self, ctx: BattleContext, spirit: BattleSpirit) -> None:
        channeling = next(
            (e for e in spirit.effects if e.type == EffectType.channeling_skill),
            None,
        )
        if not channeling or channeling.channel_skill_id != "chaosling_skill1":
            return
        channeling.channel_phase = (channeling.channel_phase or 0) + 1
        if channeling.channel_phase == 1:
            return
        if channeling.channel_phase == 2:
            spirit.effects.append(
                make_effect(
                    EffectType.stat_percent_modify,
                    spirit.unique_id,
                    remaining_turns=999,
                    is_debuff=False,
                    stat_type=StatType.atk,
                    value=0.1,
                )
            )
            spirit.effects.append(
                make_effect(
                    EffectType.stat_percent_modify,
                    spirit.unique_id,
                    remaining_turns=999,
                    is_debuff=True,
                    stat_type=StatType.def_,
                    value=-0.1,
                )
            )
            ctx.add_log(
                BattleLogType.effect_applied,
                f"{spirit.name} 狂暴蓄力第2阶段：物攻提升10%，物防降低10%！",
                {"targetId": spirit.unique_id},
            )
        elif channeling.channel_phase == 3:
            spirit.effects.append(
                make_effect(
                    EffectType.stat_percent_modify,
                    spirit.unique_id,
                    remaining_turns=999,
                    is_debuff=False,
                    stat_type=StatType.atk,
                    value=0.1,
                )
            )
            spirit.effects.append(
                make_effect(
                    EffectType.stat_percent_modify,
                    spirit.unique_id,
                    remaining_turns=999,
                    is_debuff=True,
                    stat_type=StatType.mag_def,
                    value=-0.1,
                )
            )
            ctx.add_log(
                BattleLogType.effect_applied,
                f"{spirit.name} 狂暴蓄力第3阶段：物攻提升10%，魔防降低10%！",
                {"targetId": spirit.unique_id},
            )

    def _skill_rage(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        actor.effects.append(
            make_effect(
                EffectType.stat_percent_modify,
                actor.unique_id,
                remaining_turns=999,
                is_debuff=False,
                stat_type=StatType.atk,
                value=0.1,
            )
        )
        actor.effects.append(
            make_effect(
                EffectType.stat_percent_modify,
                actor.unique_id,
                remaining_turns=999,
                is_debuff=True,
                stat_type=StatType.mag_atk,
                value=-0.1,
            )
        )
        actor.effects.append(
            make_effect(
                EffectType.channeling_skill,
                actor.unique_id,
                remaining_turns=3,
                is_debuff=False,
                channel_phase=0,
                channel_skill_id="chaosling_skill1",
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 开始狂暴蓄力！物攻提升10%，魔攻降低10%。",
            {"targetId": actor.unique_id},
        )

    def _skill_storm(self, ctx: BattleContext, actor: BattleSpirit, opponent_id: str) -> None:
        atk = get_effective_stat(actor, StatType.atk)
        for target in ctx.get_field_spirits(opponent_id):
            raw = atk * 0.8
            dmg = calculate_damage(raw, DamageType.physical, actor, target)
            actual = apply_damage(target, dmg)
            consume_next_damage_reduction(target)
            ctx.add_log(
                BattleLogType.damage_dealt,
                f"{actor.name} 的混沌风暴对 {target.name} 造成了 {actual} 点物理伤害！",
                {"attackerId": actor.unique_id, "targetId": target.unique_id, "damage": actual},
            )
            ctx.trigger_starweaver_passive(actor.owner_id, target)
            if not target.is_alive:
                ctx.add_log(BattleLogType.spirit_defeated, f"{target.name} 被击败了！", {"targetId": target.unique_id})

    def _skill_reverse(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        action: Dict[str, Any],
        opponent_id: str,
    ) -> None:
        for eff in actor.effects:
            if eff.is_debuff and eff.type == EffectType.stat_percent_modify and eff.value is not None and eff.value < 0:
                eff.value = abs(eff.value)
                eff.is_debuff = False
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 反转了自身所有能力值降低效果！",
            {"targetId": actor.unique_id},
        )
        tid = action.get("targetId")
        if not tid:
            return
        target = ctx.find_spirit_anywhere(tid)
        if target and target.is_alive and target.is_on_field:
            atk = get_effective_stat(actor, StatType.atk)
            raw = atk * 1.4
            dmg = calculate_damage(raw, DamageType.physical, actor, target)
            actual = apply_damage(target, dmg)
            consume_next_damage_reduction(target)
            ctx.add_log(
                BattleLogType.damage_dealt,
                f"{actor.name} 的命运反转对 {target.name} 造成了 {actual} 点物理伤害！",
                {"attackerId": actor.unique_id, "targetId": target.unique_id, "damage": actual},
            )
            ctx.trigger_starweaver_passive(actor.owner_id, target)
            if not target.is_alive:
                ctx.add_log(BattleLogType.spirit_defeated, f"{target.name} 被击败了！", {"targetId": target.unique_id})


chaosling_logic = ChaoslingLogic()
