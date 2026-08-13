"""裘卡 — 中毒 / 毒系爆发"""

from __future__ import annotations

from typing import Any, ClassVar, Dict

from ..battle.types import BattleLogType, BattleSpirit
from ..battle.utils import apply_poison_stacks, get_poison_stacks, process_poison_damage
from ._combat import deal_atk_ratio, target_enemy
from ..spirit_logic import BattleContext, SpiritLogic


class QiukaLogic(SpiritLogic):
    template_id = "qiuka"
    SKILLS: ClassVar[Dict[str, str]] = {
        "qiuka_skill1": "_skill_poison_sting",
        "qiuka_skill2": "_skill_virulent",
        "qiuka_skill3": "_skill_poison_claw",
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
        self._hit_physical(ctx, actor, target, 1.0, "对")
        actor.last_attack_target_id = target.unique_id
        return True

    def _hit_physical(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        target: BattleSpirit,
        ratio: float,
        verb: str,
    ) -> int:
        """Physical hit with +30% ratio against poisoned targets."""
        if not target.is_alive:
            return 0
        if get_poison_stacks(target) > 0:
            ratio *= 1.3
        return deal_atk_ratio(
            ctx,
            actor,
            target,
            ratio,
            lambda a: f"{actor.name} {verb} {target.name} 造成了 {a} 点物理伤害！",
        )

    def _add_poison(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        target: BattleSpirit,
        stacks: int,
    ) -> None:
        """Apply poison without burn cross-trigger (qiuka skill semantics)."""
        if not target.is_alive:
            return
        if apply_poison_stacks(target, actor.unique_id, stacks):
            total = get_poison_stacks(target)
            ctx.add_log(
                BattleLogType.effect_applied,
                f"{target.name} 获得 {stacks} 层中毒（当前 {total} 层）！",
                {
                    "sourceId": actor.unique_id,
                    "targetId": target.unique_id,
                    "stacks": stacks,
                },
            )

    def _skill_poison_sting(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del action
        opponent_id = ctx.get_opponent_id(player_id)
        for _ in range(7):
            enemies = ctx.get_active_spirits(opponent_id)
            if not enemies:
                return
            target = ctx.next_rng("qiuka_sting", actor.unique_id).choice(enemies)
            self._hit_physical(ctx, actor, target, 0.20, "用毒刺对")
            self._add_poison(ctx, actor, target, 1)

    def _skill_virulent(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        self._add_poison(ctx, actor, target, 3)
        process_poison_damage(ctx, target, decrease=False)

    def _skill_poison_claw(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        stacks = min(10, get_poison_stacks(target))
        self._hit_physical(ctx, actor, target, 1.0 + 0.15 * stacks, "用毒爪对")


qiuka_logic = QiukaLogic()
