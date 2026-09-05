"""蹦蹦种子 — 技能 & 被动"""

from __future__ import annotations

from typing import Any, ClassVar, Dict

from ..battle import messages as msg
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
            msg.passive(flora.name, "紧急支援"),
            {
                "floraId": flora.unique_id,
                "actorId": flora.unique_id,
                "targetId": target.unique_id,
            },
        )
        if heal > 0:
            ctx.add_log(
                BattleLogType.heal_applied,
                msg.heal(flora.name, target.name, heal),
                msg.data_heal(flora.unique_id, target.unique_id, heal),
            )
        removed = purge_debuffs(target)
        if removed:
            ctx.add_log(
                BattleLogType.effect_removed,
                msg.purged_debuffs(target.name),
                msg.data_effect(target.unique_id),
            )
        target.effects.append(
            make_effect(
                EffectType.buff_stat_percent_boost,
                flora.unique_id,
                duration_turns=1,
                stat_type=StatType.speed,
                value=0.25,
                display_name="紧急支援",
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.effect_gained(target.name, "紧急支援"),
            msg.data_effect(target.unique_id, flora.unique_id),
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
            msg.heal(actor.name, target.name, actual),
            msg.data_heal(actor.unique_id, target.unique_id, actual),
        )
        if target.unique_id == actor.unique_id:
            debuffs = [e for e in target.effects if is_debuff_effect(e.type)]
            if debuffs:
                removed = ctx.next_rng("flora_cleanse", target.unique_id).choice(debuffs)
                target.effects = [e for e in target.effects if e.id != removed.id]
                ctx.add_log(
                    BattleLogType.effect_removed,
                    msg.purged_one_debuff(target.name),
                    msg.data_effect(target.unique_id),
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
                display_name="抗逆",
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
                lambda a, t=target: msg.skill_damage(
                    actor.name, "麻醉", t.name, a, kind=msg.KIND_MAGICAL
                ),
            )
            if target.is_alive and not is_debuff_immune(target):
                target.effects.append(
                    make_effect(
                        EffectType.debuff_stat_percent_reduction,
                        actor.unique_id,
                        duration_turns=2,
                        stat_type=StatType.speed,
                        value=0.1,
                        display_name="麻醉",
                    )
                )
                ctx.add_log(
                    BattleLogType.effect_applied,
                    msg.effect_gained(target.name, "麻醉"),
                    msg.data_effect(target.unique_id, actor.unique_id),
                )


flora_logic = FloraLogic()
