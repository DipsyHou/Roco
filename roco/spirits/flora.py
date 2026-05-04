"""芙萝拉 — 技能 & 被动"""

from __future__ import annotations

from typing import Any, Dict

from ..battle_types import BattleLogType, DamageType, EffectType, StatType, BattleSpirit
from ..battle_utils import (
    apply_damage,
    apply_heal,
    calculate_damage,
    consume_next_damage_reduction,
    get_effective_stat,
    is_debuff_immune,
    make_effect,
    purge_debuffs,
)
from ..spirit_logic import BattleContext, SpiritLogic


class FloraLogic(SpiritLogic):
    template_id = "flora"

    def on_init(self, spirit: BattleSpirit) -> None:
        spirit.passive_triggered = False

    def execute_skill(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        op = ctx.get_opponent_id(player_id)
        sk = action.get("skillId")
        if sk == "flora_skill1":
            self._skill_heal(ctx, actor, action)
        elif sk == "flora_skill2":
            self._skill_pain_relief(ctx, actor, action)
        elif sk == "flora_skill3":
            self._skill_bandage(ctx, actor, op)

    def check_passive(self, ctx: BattleContext, player_id: str) -> None:
        all_spirits = ctx.get_all_spirits(player_id)
        flora = next(
            (
                s
                for s in all_spirits
                if s.template_id == "flora" and s.is_alive and not (s.passive_triggered or False)
            ),
            None,
        )
        if not flora:
            return

        field_others = [
            s
            for s in all_spirits
            if s.is_on_field and s.is_alive and s.unique_id != flora.unique_id
        ]
        for spirit in field_others:
            if spirit.current_hp / spirit.max_hp < 0.25:
                flora.passive_triggered = True
                mag = get_effective_stat(flora, StatType.mag_atk)
                heal = apply_heal(spirit, mag * 1.0)
                ctx.add_log(
                    BattleLogType.passive_triggered,
                    f"{flora.name} 的后勤支援触发！为 {spirit.name} 回复了 {heal} 点血量！",
                    {"floraId": flora.unique_id, "targetId": spirit.unique_id},
                )
                removed = purge_debuffs(spirit)
                if removed:
                    ctx.add_log(
                        BattleLogType.effect_removed,
                        f"{spirit.name} 的负面效果被净化了！",
                        {"targetId": spirit.unique_id},
                    )
                spirit.effects.append(
                    make_effect(
                        EffectType.stat_percent_modify,
                        flora.unique_id,
                        remaining_turns=2,
                        is_debuff=False,
                        stat_type=StatType.speed,
                        value=0.3,
                    )
                )
                ctx.add_log(
                    BattleLogType.effect_applied,
                    f"{spirit.name} 速度提升了30%，持续1回合！",
                    {"targetId": spirit.unique_id},
                )
                return

    def _skill_heal(self, ctx: BattleContext, actor: BattleSpirit, action: Dict[str, Any]) -> None:
        tid = action.get("targetId")
        if not tid:
            return
        target = ctx.find_spirit_anywhere(tid)
        if not target or not target.is_alive:
            return
        mag = get_effective_stat(actor, StatType.mag_atk)
        amt = mag * 0.8
        if target.is_on_field:
            amt += mag * 0.4
        actual = apply_heal(target, amt)
        ctx.add_log(
            BattleLogType.heal_applied,
            f"{actor.name} 为 {target.name} 回复了 {actual} 点血量！",
            {"actorId": actor.unique_id, "targetId": target.unique_id, "heal": actual},
        )

    def _skill_pain_relief(self, ctx: BattleContext, actor: BattleSpirit, action: Dict[str, Any]) -> None:
        tid = action.get("targetId")
        if not tid:
            return
        target = ctx.find_spirit_anywhere(tid)
        if not target or not target.is_alive or not target.is_on_field:
            return
        target.effects.append(
            make_effect(
                EffectType.next_damage_reduction,
                actor.unique_id,
                remaining_turns=-1,
                is_debuff=False,
                reduction_percent=0.15,
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{target.name} 获得了止痛效果，下次受伤减少15%！",
            {"targetId": target.unique_id},
        )

    def _skill_bandage(self, ctx: BattleContext, actor: BattleSpirit, opponent_id: str) -> None:
        mag = get_effective_stat(actor, StatType.mag_atk)
        for target in ctx.get_field_spirits(opponent_id):
            raw = mag * 0.8
            dmg = calculate_damage(raw, DamageType.magical, actor, target)
            actual = apply_damage(target, dmg)
            consume_next_damage_reduction(target)
            ctx.add_log(
                BattleLogType.damage_dealt,
                f"{actor.name} 的绷带束缚对 {target.name} 造成了 {actual} 点魔法伤害！",
                {"attackerId": actor.unique_id, "targetId": target.unique_id, "damage": actual},
            )
            if target.is_alive and not is_debuff_immune(target):
                target.effects.append(
                    make_effect(
                        EffectType.stat_percent_modify,
                        actor.unique_id,
                        remaining_turns=3,
                        is_debuff=True,
                        stat_type=StatType.speed,
                        value=-0.1,
                    )
                )
                ctx.add_log(
                    BattleLogType.effect_applied,
                    f"{target.name} 速度降低了10%，持续2回合！",
                    {"targetId": target.unique_id},
                )
            ctx.trigger_starweaver_passive(actor.owner_id, target)
            if not target.is_alive:
                ctx.add_log(
                    BattleLogType.spirit_defeated,
                    f"{target.name} 被击败了！",
                    {"targetId": target.unique_id},
                )


flora_logic = FloraLogic()
