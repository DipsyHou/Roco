"""蒸汽神龙 — 升温 / 灼烧 / 相邻普攻溅射"""

from __future__ import annotations

from typing import Any, ClassVar, Dict

from ..battle.types import BattleLogType, BattleSpirit, EffectType
from ..battle.utils import (
    add_warmup_stacks,
    apply_burn_stacks,
    apply_heal,
    get_total_burn_stacks,
    get_warmup_stacks,
)
from ._combat import deal_atk_ratio, target_enemy
from ..spirit_logic import BattleContext, SpiritLogic


class SteamdragonLogic(SpiritLogic):
    template_id = "steamdragon"
    SKILLS: ClassVar[Dict[str, str]] = {
        "steamdragon_skill1": "_skill_brand",
        "steamdragon_skill2": "_skill_heat_appetite",
        "steamdragon_skill3": "_skill_boil",
    }

    def on_turn_start(self, ctx: BattleContext, spirit: BattleSpirit) -> None:
        add_warmup_stacks(spirit, spirit.unique_id, 2)
        stacks = get_warmup_stacks(spirit)
        ctx.add_log(
            BattleLogType.passive_triggered,
            f"{spirit.name} 的热启动获得 2 层升温（当前 {stacks} 层）！",
            {"actorId": spirit.unique_id, "warmupStacks": stacks},
        )

    def on_attack_hit(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        target: BattleSpirit,
        damage: int,
    ) -> None:
        del player_id, damage
        if actor.template_id != self.template_id or not target.is_alive:
            return
        stacks = get_warmup_stacks(actor)
        if stacks <= 0:
            return
        if apply_burn_stacks(target, actor.unique_id, stacks):
            total = sum(
                e.stacks
                for e in target.effects
                if e.type == EffectType.debuff_burn and e.source_id == actor.unique_id
            )
            ctx.add_log(
                BattleLogType.effect_applied,
                f"{actor.name} 的升温使 {target.name} 获得 {stacks} 层灼烧（该来源共 {total} 层）！",
                {
                    "sourceId": actor.unique_id,
                    "targetId": target.unique_id,
                    "stacks": stacks,
                },
            )

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
            0.5,
            lambda a: f"{actor.name} 对 {target.name} 造成了 {a} 点物理伤害！",
        )
        for adj in ctx.get_adjacent_enemies(target):
            if adj.is_alive:
                deal_atk_ratio(
                    ctx,
                    actor,
                    adj,
                    0.25,
                    lambda a, t=adj: f"{actor.name} 对 {t.name} 造成了 {a} 点物理伤害！",
                )
        actor.last_attack_target_id = target.unique_id
        return True

    def _skill_brand(
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
            0.5,
            lambda a: f"{actor.name} 对 {target.name} 造成了 {a} 点物理伤害！",
        )
        # Brand burn does not cross-trigger poison (unlike grant_burn).
        if target.is_alive and apply_burn_stacks(target, actor.unique_id, 5):
            ctx.add_log(
                BattleLogType.effect_applied,
                f"{target.name} 获得 5 层灼烧！",
                {"targetId": target.unique_id, "sourceId": actor.unique_id},
            )

    def _skill_heat_appetite(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del action
        opponent_id = ctx.get_opponent_id(player_id)
        total_burn = sum(
            get_total_burn_stacks(enemy) for enemy in ctx.get_active_spirits(opponent_id)
        )
        heal = apply_heal(actor, total_burn * 8)
        ctx.add_log(
            BattleLogType.heal_applied,
            f"{actor.name} 的嗜热回复了 {heal} 点生命（敌方灼烧合计 {total_burn} 层）！",
            {"actorId": actor.unique_id, "heal": heal, "burnStacks": total_burn},
        )

    def _skill_boil(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id, action
        cost = int(actor.max_hp * 0.25)
        actual_cost = min(actor.current_hp - 1, cost) if actor.current_hp > 1 else 0
        if actual_cost > 0:
            actor.current_hp -= actual_cost
            ctx.add_log(
                BattleLogType.damage_dealt,
                f"{actor.name} 为沸腾消耗了 {actual_cost} 点生命！",
                {"targetId": actor.unique_id, "damage": actual_cost},
            )
        before = get_warmup_stacks(actor)
        add_warmup_stacks(actor, actor.unique_id, 4)
        stacks = get_warmup_stacks(actor)
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 的沸腾获得 4 层升温（{before} → {stacks} 层）！",
            {"actorId": actor.unique_id, "warmupStacks": stacks},
        )


steamdragon_logic = SteamdragonLogic()
