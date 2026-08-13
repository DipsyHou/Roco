"""蹦蹦种子 — 技能 & 被动"""

from __future__ import annotations

from typing import Any, ClassVar, Dict

from ..battle.types import BattleLogType, EffectType, StatType, BattleSpirit
from ..battle.utils import (
    apply_heal,
    get_effective_stat,
    is_debuff_effect,
    is_debuff_immune,
    make_effect,
    purge_debuffs,
)
from ._combat import deal_mag_ratio
from ..spirit_logic import BattleContext, DamageEvent, SpiritLogic


class FloraLogic(SpiritLogic):
    template_id = "flora"
    SKILLS: ClassVar[Dict[str, str]] = {
        "flora_skill1": "_skill_heal",
        "flora_skill2": "_skill_pain_relief",
        "flora_skill3": "_skill_bandage",
    }

    def on_unit_created(self, spirit: BattleSpirit) -> None:
        spirit.passive_triggered = False

    def describe_extra_states(self, spirit: BattleSpirit) -> list:
        """紧急支援是一次性被动，未触发时在状态栏提示待命。"""
        if spirit.passive_triggered is False:
            return ["[state]紧急支援就绪"]
        return []

    def describe_avatar_badge(self, spirit: BattleSpirit):
        if spirit.template_id != self.template_id:
            return None
        # 紧急支援未触发计为 1，已触发计为 0。
        ready = 0 if spirit.passive_triggered else 1
        return ("蹦蹦种子", str(ready))

    def on_damage(self, ctx: BattleContext, spirit: BattleSpirit, event: DamageEvent) -> None:
        if spirit.template_id != self.template_id:
            return
        if not spirit.is_alive or spirit.passive_triggered:
            return
        if event.damage <= 0:
            return
        target = event.target
        if not target.is_alive or target.owner_id != spirit.owner_id:
            return
        if target.current_hp / target.max_hp >= 0.30:
            return
        self._trigger_emergency_support(ctx, spirit, target)

    def _trigger_emergency_support(
        self,
        ctx: BattleContext,
        flora: BattleSpirit,
        target: BattleSpirit,
    ) -> None:
        flora.passive_triggered = True
        mag = get_effective_stat(flora, StatType.mag_atk)
        heal = apply_heal(target, mag * 1.0)
        ctx.add_log(
            BattleLogType.passive_triggered,
            f"{flora.name} 的紧急支援触发！为 {target.name} 回复了 {heal} 点血量！",
            {"floraId": flora.unique_id, "targetId": target.unique_id},
        )
        removed = purge_debuffs(target)
        if removed:
            ctx.add_log(
                BattleLogType.effect_removed,
                f"{target.name} 的负面效果被净化了！",
                {"targetId": target.unique_id},
            )
        target.effects.append(
            make_effect(
                EffectType.buff_stat_percent_boost,
                flora.unique_id,
                duration_turns=1,
                stat_type=StatType.speed,
                value=0.25,
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{target.name} 速度提升了25%，持续1回合！",
            {"targetId": target.unique_id},
        )

    def _skill_heal(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id
        tid = action.get("targetId")
        if not tid:
            return
        target = ctx.find_spirit_anywhere(tid)
        if not target or not target.is_alive:
            return
        mag = get_effective_stat(actor, StatType.mag_atk)
        actual = apply_heal(target, mag * 0.80)
        ctx.add_log(
            BattleLogType.heal_applied,
            f"{actor.name} 为 {target.name} 回复了 {actual} 点血量！",
            {"actorId": actor.unique_id, "targetId": target.unique_id, "heal": actual},
        )
        if target.unique_id == actor.unique_id:
            debuffs = [e for e in target.effects if is_debuff_effect(e.type)]
            if debuffs:
                removed = ctx.next_rng("flora_cleanse", target.unique_id).choice(debuffs)
                target.effects = [e for e in target.effects if e.id != removed.id]
                ctx.add_log(
                    BattleLogType.effect_removed,
                    f"{target.name} 的一个负面效果被解除了！",
                    {"targetId": target.unique_id},
                )

    def _skill_pain_relief(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id
        tid = action.get("targetId")
        if not tid:
            return
        target = ctx.find_spirit_anywhere(tid)
        if not target or not target.is_alive:
            return
        target.effects.append(
            make_effect(
                EffectType.buff_taken_damage_percent_reduction,
                actor.unique_id,
                duration_turns=2,
                value=0.20,
            )
        )

    def _skill_bandage(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del action
        opponent_id = ctx.get_opponent_id(player_id)
        for target in ctx.get_active_spirits(opponent_id):
            deal_mag_ratio(
                ctx,
                actor,
                target,
                0.5,
                lambda a, t=target: f"{actor.name} 的麻醉对 {t.name} 造成了 {a} 点魔法伤害！",
            )
            if target.is_alive and not is_debuff_immune(target):
                target.effects.append(
                    make_effect(
                        EffectType.debuff_stat_percent_reduction,
                        actor.unique_id,
                        duration_turns=2,
                        stat_type=StatType.speed,
                        value=0.1,
                    )
                )
                ctx.add_log(
                    BattleLogType.effect_applied,
                    f"{target.name} 速度降低了10%，持续2回合！",
                    {"targetId": target.unique_id},
                )


flora_logic = FloraLogic()
