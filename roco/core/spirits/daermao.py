"""大耳帽兜 — 纯白 / 轻雾 / 飞霰 / 冰冻 / 萌化"""

from __future__ import annotations

from typing import Any, ClassVar, Dict

from ..battle import messages as msg
from ..battle.effects import (
    apply_freeze_stacks,
    apply_skill_energy_cost_increase,
    count_buff_effects,
    get_freeze_stacks,
    purge_random_buffs,
)
from ..battle.types import BattleLogType, BattleSpirit, EffectType
from ..battle.utils import make_effect
from ._combat import deal_atk_ratio, target_enemy
from ..spirit_logic import BattleContext, SpiritLogic

TEMPLATE_ID = "daermao"
QINGWU_DISPLAY = "全技能能耗+1"
MENGHUA_DISPLAY = "萌化"


class DaermaoLogic(SpiritLogic):
    template_id = TEMPLATE_ID
    SKILLS: ClassVar[Dict[str, str]] = {
        "daermao_skill1": "_skill_qingwu",
        "daermao_skill2": "_skill_feixian",
        "daermao_skill3": "_skill_menghua",
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

    def _skill_qingwu(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        self._trigger_chunbai(ctx, actor, target)
        if apply_skill_energy_cost_increase(
            target,
            actor.unique_id,
            increase=1,
            duration_turns=3,
            display_name=QINGWU_DISPLAY,
        ):
            ctx.add_log(
                BattleLogType.effect_applied,
                msg.effect_gained(target.name, "全技能能耗+1"),
                msg.data_effect(target.unique_id, actor.unique_id),
            )

    def _skill_feixian(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        self._trigger_chunbai(ctx, actor, target)
        if apply_freeze_stacks(target, actor.unique_id, 6):
            ctx.add_log(
                BattleLogType.effect_applied,
                msg.gained_stacks(
                    target.name, 6, "冰冻", total=get_freeze_stacks(target)
                ),
                msg.data_effect(
                    target.unique_id,
                    actor.unique_id,
                    stacks=get_freeze_stacks(target),
                ),
            )
        for adj in ctx.get_adjacent_enemies(target):
            if not adj.is_alive:
                continue
            if apply_freeze_stacks(adj, actor.unique_id, 3):
                ctx.add_log(
                    BattleLogType.effect_applied,
                    msg.gained_stacks(
                        adj.name, 3, "冰冻", total=get_freeze_stacks(adj)
                    ),
                    msg.data_effect(
                        adj.unique_id,
                        actor.unique_id,
                        stacks=get_freeze_stacks(adj),
                    ),
                )

    def _skill_menghua(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        self._trigger_chunbai(ctx, actor, target)
        existing = next(
            (
                effect
                for effect in target.effects
                if effect.type == EffectType.debuff_damage_percent_reduction
                and effect.damage_type is None
                and effect.display_name == MENGHUA_DISPLAY
            ),
            None,
        )
        if existing:
            return
        target.effects.append(
            make_effect(
                EffectType.debuff_damage_percent_reduction,
                actor.unique_id,
                duration_turns=2,
                value=0.33,
                display_name=MENGHUA_DISPLAY,
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.effect_gained(target.name, "萌化"),
            msg.data_effect(target.unique_id, actor.unique_id),
        )

    def _trigger_chunbai(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        target: BattleSpirit,
    ) -> None:
        if not target.is_alive:
            return
        buff_count = count_buff_effects(target)
        if buff_count < 2:
            return
        purge_count = 1 if buff_count <= 3 else 2
        removed = purge_random_buffs(
            target, purge_count, ctx.next_rng("daermao_chunbai", target.unique_id)
        )
        if not removed:
            return
        ctx.add_log(
            BattleLogType.passive_triggered,
            msg.purged_buffs(target.name, len(removed), source=actor.name),
            msg.data_effect(
                target.unique_id, actor.unique_id, count=len(removed)
            ),
        )


daermao_logic = DaermaoLogic()
