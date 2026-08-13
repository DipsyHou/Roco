"""凡鹰 — 速度光环 / 行动提前"""

from __future__ import annotations

from typing import Any, ClassVar, Dict

from ..battle.types import BattleLogType, BattleSpirit, EffectType, StatType
from ..battle.utils import is_debuff_immune, make_effect
from ._combat import deal_atk_ratio, target_enemy
from ..spirit_logic import BattleContext, DamageEvent, SpiritLogic


class FanyingLogic(SpiritLogic):
    template_id = "fanying"
    SKILLS: ClassVar[Dict[str, str]] = {
        "fanying_skill1": "_skill_cyclone",
        "fanying_skill2": "_skill_wing_guard",
        "fanying_skill3": "_skill_your_turn",
    }

    def on_battle_start(self, ctx: BattleContext, spirit: BattleSpirit) -> None:
        spirit.effects = [e for e in spirit.effects if e.type != EffectType.state_tailwind]
        spirit.effects.append(
            make_effect(
                EffectType.state_tailwind,
                spirit.unique_id,
                display_name="破风",
            )
        )

    def get_aura_stat_percent_bonus(
        self,
        ctx: BattleContext,
        source: BattleSpirit,
        target: BattleSpirit,
        stat: StatType,
    ) -> float:
        if stat != StatType.speed or not source.is_alive:
            return 0.0
        bonus = 0.0
        if source.owner_id == target.owner_id and any(
            e.type == EffectType.state_tailwind for e in source.effects
        ):
            if source.unique_id == target.unique_id:
                bonus += 0.08
            elif any(
                s.unique_id == target.unique_id
                for s in ctx.get_adjacent_allies(source, source.owner_id)
                if s.unique_id != source.unique_id
            ):
                bonus += 0.04
        if any(
            e.type == EffectType.state_wing_guard and e.source_id == source.unique_id
            for e in target.effects
        ):
            bonus += 0.08
        return bonus

    def on_damage(self, ctx: BattleContext, spirit: BattleSpirit, event: DamageEvent) -> None:
        target = event.target
        damage = event.damage
        if not spirit.is_alive or not target.is_alive or damage <= 0:
            return
        guard = next((e for e in target.effects if e.type == EffectType.state_wing_guard), None)
        if not guard or guard.source_id != spirit.unique_id:
            return
        before = target.charge
        ctx.advance_action(target, 0.05)
        if target.charge < before:
            ctx.add_log(
                BattleLogType.passive_triggered,
                f"{target.name} 的羽翼守护使其行动提前5%！",
                {"targetId": target.unique_id, "sourceId": spirit.unique_id},
            )

    def on_spirit_defeated(
        self,
        ctx: BattleContext,
        spirit: BattleSpirit,
        defeated: BattleSpirit,
    ) -> None:
        if defeated.unique_id != spirit.unique_id:
            return
        for ally in ctx.get_all_spirits(spirit.owner_id):
            ally.effects = [
                e
                for e in ally.effects
                if not (e.type == EffectType.state_wing_guard and e.source_id == spirit.unique_id)
            ]

    def execute_normal_attack(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> bool:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return True
        deal_atk_ratio(
            ctx,
            actor,
            target,
            1.0,
            lambda a: f"{actor.name} 对 {target.name} 造成了 {a} 点物理伤害！",
        )
        actor.last_attack_target_id = target.unique_id
        return True

    def _skill_cyclone(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        deal_atk_ratio(
            ctx,
            actor,
            target,
            0.8,
            lambda a: f"{actor.name} 的气旋对 {target.name} 造成了 {a} 点物理伤害！",
        )
        if target.is_alive and not is_debuff_immune(target):
            target.effects.append(
                make_effect(
                    EffectType.debuff_stat_percent_reduction,
                    actor.unique_id,
                    duration_turns=1,
                    stat_type=StatType.speed,
                    value=0.15,
                )
            )
            ctx.add_log(
                BattleLogType.effect_applied,
                f"{target.name} 的速度降低15%（1回合）！",
                {"targetId": target.unique_id},
            )
        for adj in ctx.get_adjacent_enemies(target):
            deal_atk_ratio(
                ctx,
                actor,
                adj,
                0.4,
                lambda a, t=adj: f"{actor.name} 的气旋余波对 {t.name} 造成了 {a} 点物理伤害！",
            )

    def _skill_wing_guard(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = ctx.find_spirit_anywhere(action.get("targetId") or "")
        if not target or not target.is_alive or target.owner_id != player_id:
            return
        for ally in ctx.get_all_spirits(player_id):
            ally.effects = [
                e
                for e in ally.effects
                if not (e.type == EffectType.state_wing_guard and e.source_id == actor.unique_id)
            ]
        target.effects.append(
            make_effect(
                EffectType.state_wing_guard,
                actor.unique_id,
                display_name="羽翼守护",
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{target.name} 获得了羽翼守护！",
            {"targetId": target.unique_id, "sourceId": actor.unique_id},
        )

    def _skill_your_turn(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = ctx.find_spirit_anywhere(action.get("targetId") or "")
        if not target or not target.is_alive:
            return
        ctx.advance_action(target, 1.0)
        if target.owner_id == player_id:
            # Self-targeting ticks once at this turn's end, so seed one extra turn.
            duration_turns = 2 if target.unique_id == actor.unique_id else 1
            target.effects.append(
                make_effect(
                    EffectType.buff_damage_percent_boost,
                    actor.unique_id,
                    duration_turns=duration_turns,
                    value=0.2,
                    display_name="伤害提升",
                )
            )
            ctx.add_log(
                BattleLogType.effect_applied,
                f"{target.name} 获得了20%伤害提升（1回合）！",
                {"targetId": target.unique_id},
            )
        elif not is_debuff_immune(target):
            target.effects.append(
                make_effect(EffectType.debuff_stun, actor.unique_id, duration_turns=1)
            )
            ctx.add_log(
                BattleLogType.effect_applied,
                f"{target.name} 被晕眩1回合！",
                {"targetId": target.unique_id},
            )
        ctx.add_log(
            BattleLogType.action_executed,
            f"{actor.name} 使 {target.name} 下一回合提前100%！",
            {"actorId": actor.unique_id, "targetId": target.unique_id},
        )


fanying_logic = FanyingLogic()
