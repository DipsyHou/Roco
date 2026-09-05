"""尖嘴狐仙 — 灼烧 / 中毒 / 内爆"""

from __future__ import annotations

from typing import Any, ClassVar, Dict

from ..battle import messages as msg
from ..battle.types import BattleSpirit
from ..battle.utils import get_total_burn_stacks
from ._combat import deal_atk_ratio, grant_burn, grant_poison, target_enemy
from ..spirit_logic import BattleContext, DamageSource, SpiritLogic


class HuxianLogic(SpiritLogic):
    template_id = "huxian"
    SKILLS: ClassVar[Dict[str, str]] = {
        "huxian_skill1": "_skill_brand",
        "huxian_skill2": "_skill_ghost_fire",
        "huxian_skill3": "_skill_fan_wind",
    }

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
            lambda a: msg.physical_hit(actor.name, target.name, a),
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
            lambda a: msg.skill_damage(actor.name, "烙印", target.name, a),
            source=DamageSource.skill,
        )
        if target.is_alive:
            grant_burn(ctx, actor, target, 5)

    def _skill_ghost_fire(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id
        target = target_enemy(ctx, actor.owner_id, action.get("targetId"))
        if not target:
            return
        grant_poison(ctx, actor, target, 4)
        if target.is_alive:
            grant_burn(ctx, actor, target, 4)

    def _skill_fan_wind(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id
        target = target_enemy(ctx, actor.owner_id, action.get("targetId"))
        if not target:
            return
        grant_burn(
            ctx,
            actor,
            target,
            4,
            log_message=msg.gained_stacks(target.name, 4, "灼烧"),
        )
        if not target.is_alive:
            return
        splash = get_total_burn_stacks(target) // 2
        if splash <= 0:
            return
        for adj in ctx.get_adjacent_enemies(target):
            if adj.is_alive:
                grant_burn(
                    ctx,
                    actor,
                    adj,
                    splash,
                    log_message=msg.gained_stacks(adj.name, splash, "灼烧"),
                )


huxian_logic = HuxianLogic()
