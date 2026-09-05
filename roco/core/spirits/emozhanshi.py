"""恶魔战士 — 肉盾 / 血墙 / 狂宴 / 临行留念。

- 肉盾（被动）：开局给自身挂“肉盾”状态。基于自身（物防+魔防）之和的 8%，为全队（含自身）
  的物防与魔防各提供固定加成——这是一类「转化」，其底数排除转化类加成，故不会二次转化 /
  递归（见 stats.py::_conversion_flat_bonus 与 docs/mechanics.md 第 8 节）；同时使自身
  受到的伤害提高 50%（经 get_damage_reduction 注入伤害管线）。
- 血墙：直接消耗 10% 最大生命（不视为受击、至少保留 1 点），获得可重置的双防提升。
- 狂宴：回复已损生命的 50%。
- 临行留念：对全体敌人造成魔法伤害（按施放瞬间当前生命计），随后自身直接倒下（触发 on_death）。
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List

from ..battle import messages as msg
from ..battle.events import DamageSource
from ..battle.hp import execute_instant_defeat
from ..battle.types import (
    BattleLogType,
    BattleSpirit,
    DamageType,
    EffectType,
    StatType,
)
from ..battle.utils import get_effective_stat, make_effect
from ._combat import deal_damage, deal_heal
from ..spirit_logic import BattleContext, SpiritLogic

TEMPLATE_ID = "emozhanshi"
ROUDUN_RATIO = 0.08
ROUDUN_TAKEN_BOOST = 0.50
XUEQIANG_TAG = "emozhanshi_xueqiang"
XUEQIANG_COST_RATIO = 0.10
XUEQIANG_DEF_BONUS = 0.50
XUEQIANG_DURATION = 4
KUANGYAN_HEAL_RATIO = 0.33
LINXING_MAG_RATIO = 0.50
LINXING_HP_RATIO = 0.10


def _has_effect(spirit: BattleSpirit, eff_type: EffectType) -> bool:
    return any(effect.type == eff_type for effect in spirit.effects)


class EmozhanshiLogic(SpiritLogic):
    template_id = TEMPLATE_ID
    SKILLS: ClassVar[Dict[str, str]] = {
        "emozhanshi_skill1": "_skill_xueqiang",
        "emozhanshi_skill2": "_skill_kuangyan",
        "emozhanshi_skill3": "_skill_linxing",
    }

    def on_battle_start(self, ctx: BattleContext, spirit: BattleSpirit) -> None:
        if spirit.template_id != TEMPLATE_ID:
            return
        if not _has_effect(spirit, EffectType.state_roudun):
            spirit.effects.append(
                make_effect(
                    EffectType.state_roudun,
                    spirit.unique_id,
                    value=ROUDUN_RATIO,
                    display_name="肉盾",
                )
            )
        ctx.add_log(
            BattleLogType.passive_triggered,
            msg.effect_gained(spirit.name, "肉盾"),
            msg.data_effect(spirit.unique_id, spirit.unique_id),
        )

    def get_damage_reduction(self, spirit: BattleSpirit) -> float:
        if spirit.template_id != TEMPLATE_ID:
            return 0.0
        return -ROUDUN_TAKEN_BOOST if _has_effect(spirit, EffectType.state_roudun) else 0.0

    # --- skills ---

    def _skill_xueqiang(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id, action
        cost = int(actor.max_hp * XUEQIANG_COST_RATIO)
        actor.current_hp = max(1, actor.current_hp - cost)
        actor.effects = [e for e in actor.effects if e.effect_tag != XUEQIANG_TAG]
        for stat in (StatType.def_, StatType.mag_def):
            actor.effects.append(
                make_effect(
                    EffectType.buff_stat_percent_boost,
                    actor.unique_id,
                    duration_turns=XUEQIANG_DURATION,
                    stat_type=stat,
                    value=XUEQIANG_DEF_BONUS,
                    effect_tag=XUEQIANG_TAG,
                    display_name="血墙",
                )
            )
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.effect_gained(actor.name, "血墙"),
            msg.data_effect(actor.unique_id, actor.unique_id),
        )

    def _skill_kuangyan(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id, action
        missing = max(0, actor.max_hp - actor.current_hp)
        deal_heal(
            ctx,
            actor,
            actor,
            missing * KUANGYAN_HEAL_RATIO,
            lambda a: msg.heal_self(actor.name, a, skill="狂宴"),
        )

    def _skill_linxing(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del action
        missing_hp = max(0, actor.max_hp - actor.current_hp)
        raw = (
            get_effective_stat(actor, StatType.mag_atk) * LINXING_MAG_RATIO
            + missing_hp * LINXING_HP_RATIO
        )
        opponent_id = ctx.get_opponent_id(player_id)
        targets: List[BattleSpirit] = [
            enemy for enemy in ctx.get_active_spirits(opponent_id) if enemy.is_alive
        ]
        for target in targets:
            deal_damage(
                ctx,
                actor,
                target,
                raw,
                DamageType.magical,
                lambda a, t=target: msg.skill_damage(
                    actor.name, "临行留念", t.name, a, kind=msg.KIND_MAGICAL
                ),
                source=DamageSource.skill,
                crit_rng=ctx.next_rng("emozhanshi_linxing_crit", actor.unique_id, target.unique_id),
            )
        execute_instant_defeat(
            actor,
            ctx=ctx,
            log_message=msg.defeated(actor.name),
        )


emozhanshi_logic = EmozhanshiLogic()
