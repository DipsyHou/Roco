"""格鲁姆 — 养分输送 / 深根 / 寄生 / 紧缠。"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, Optional

from ..battle.events import DamageEvent
from ..battle.types import (
    BattleLogType,
    BattleSpirit,
    DamageType,
    EffectType,
    StatType,
)
from ..battle.utils import apply_heal, make_effect
from ._combat import (
    deal_atk_ratio,
    grant_parasite,
    target_enemy,
)
from ..battle.dot import trigger_parasite_damage
from ..spirit_logic import BattleContext, SpiritLogic

TEMPLATE_ID = "gulum"
SHENGEN_DURATION = 3
SHENGEN_SPEED_PENALTY = -0.40
NUTRIENT_HEAL_RATIO = 0.02
SEED_PARASITE_STACKS = 4
TANGLE_PARASITE_STACKS = 2
NORMAL_ATK_RATIO = 1.0


def _get_shengen(spirit: BattleSpirit):
    return next((e for e in spirit.effects if e.type == EffectType.state_shengen), None)


def _has_shengen(spirit: BattleSpirit) -> bool:
    return _get_shengen(spirit) is not None


class GulumLogic(SpiritLogic):
    template_id = TEMPLATE_ID
    SKILLS: ClassVar[Dict[str, str]] = {
        "gulum_skill1": "_skill_seed",
        "gulum_skill2": "_skill_shengen",
        "gulum_skill3": "_skill_tangle",
    }

    def get_stat_percent_bonus(self, spirit: BattleSpirit, stat: StatType) -> float:
        if spirit.template_id != self.template_id or stat != StatType.speed:
            return 0.0
        if _has_shengen(spirit):
            return SHENGEN_SPEED_PENALTY
        return 0.0

    def get_damage_share_for_ally(
        self,
        ctx: BattleContext,
        observer: BattleSpirit,
        ally: BattleSpirit,
        segment_amount: int,
    ) -> int:
        del ctx
        if observer.template_id != self.template_id or segment_amount <= 0:
            return 0
        if not _has_shengen(observer):
            return 0
        if ally.owner_id != observer.owner_id or ally.unique_id == observer.unique_id:
            return 0
        return segment_amount // 2

    def on_damage(self, ctx: BattleContext, spirit: BattleSpirit, event: DamageEvent) -> None:
        if spirit.template_id != self.template_id or not spirit.is_alive:
            return
        if event.damage <= 0:
            return
        target = event.target
        if target.owner_id != spirit.owner_id or target.unique_id == spirit.unique_id:
            return

        heal_amt = int(spirit.max_hp * NUTRIENT_HEAL_RATIO + 1e-9)
        if heal_amt <= 0:
            return

        spirit_ratio = spirit.current_hp / spirit.max_hp if spirit.max_hp > 0 else 0.0
        if spirit_ratio > 0.5:
            recipient = target
            log_line = (
                f"{spirit.name} 的养分输送为 {target.name} 回复了 {{actual}} 点血量！"
            )
        else:
            recipient = spirit
            log_line = f"{spirit.name} 的养分输送为自己回复了 {{actual}} 点血量！"

        actual = apply_heal(recipient, heal_amt)
        if actual > 0:
            ctx.add_log(
                BattleLogType.heal_applied,
                log_line.format(actual=actual),
                {
                    "actorId": spirit.unique_id,
                    "targetId": recipient.unique_id,
                    "heal": actual,
                },
            )

    def execute_normal_attack(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> bool:
        if actor.template_id != self.template_id:
            return False
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return True
        deal_atk_ratio(
            ctx,
            actor,
            target,
            NORMAL_ATK_RATIO,
            lambda actual: (
                f"{actor.name} 的普通攻击对 {target.name} 造成了 {actual} 点物理伤害！"
            ),
        )
        return True

    def _skill_seed(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if target:
            grant_parasite(ctx, actor, target, SEED_PARASITE_STACKS)

    def _skill_shengen(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id, action
        existing = _get_shengen(actor)
        if existing:
            existing.duration_turns = SHENGEN_DURATION
            ctx.add_log(
                BattleLogType.effect_applied,
                f"{actor.name} 刷新了「深根」！",
                {"targetId": actor.unique_id, "sourceId": actor.unique_id},
            )
            return
        actor.effects.append(
            make_effect(
                EffectType.state_shengen,
                actor.unique_id,
                duration_turns=SHENGEN_DURATION,
                display_name="深根",
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 获得了「深根」！",
            {"targetId": actor.unique_id, "sourceId": actor.unique_id},
        )

    def _skill_tangle(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del action
        opponent_id = ctx.get_opponent_id(player_id)
        enemies = [enemy for enemy in ctx.get_active_spirits(opponent_id) if enemy.is_alive]
        for enemy in enemies:
            grant_parasite(ctx, actor, enemy, TANGLE_PARASITE_STACKS)
        for enemy in enemies:
            if enemy.is_alive:
                trigger_parasite_damage(ctx, enemy)


gulum_logic = GulumLogic()
