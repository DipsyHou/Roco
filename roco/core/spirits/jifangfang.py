"""机械方方 — 多色模块 / 防火墙 / 便携防火墙 / 超限模块。

- 多色模块（被动）：开局获得「强化模块」。每次使用技能后，按
  强化 → 急速 → 抵御 → 强化 循环切换当前模块。三种模块的增益（造成伤害 +12% /
  速度 +6% / 受到伤害 −12%）作用于「拥有本方方所提供护盾」的目标，
  由 battle/shield.py 的模块光环统一注入伤害 / 速度管线。
- 防火墙 / 便携防火墙：为己方赋予护盾（来源相同故合并为一条，见 §22 来源归并）。
- 超限模块：4 回合内同时具备三种模块效果。
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List

from ..battle import messages as msg
from ..battle.shield import grant_shield, has_shield_from
from ..battle.types import (
    BattleLogType,
    BattleSpirit,
    EffectType,
    StatType,
)
from ..battle.utils import get_effective_stat, make_effect
from ._combat import target_ally
from ..spirit_logic import BattleContext, SpiritLogic

TEMPLATE_ID = "jifangfang"

FANGHUOQIANG_RATIO = 0.60
FANGHUOQIANG_CAP_RATIO = 1.20
FANGHUOQIANG_DURATION = 3
BIANXIE_RATIO = 0.30
BIANXIE_CAP_RATIO = 1.20
BIANXIE_DURATION = 3
CHAOXIAN_DURATION = 4

# 模块光环数值：作用于「持有本方方所提供护盾」的己方目标。
MODULE_DAMAGE_BONUS = 0.12
MODULE_SPEED_BONUS = 0.06
MODULE_TAKEN_REDUCTION = 0.12

SKILL_FANGHUOQIANG = "jifangfang_skill1"
SKILL_BIANXIE = "jifangfang_skill2"
SKILL_CHAOXIAN = "jifangfang_skill3"

_MODULE_ORDER: List[EffectType] = [
    EffectType.state_module_qianghua,
    EffectType.state_module_jisu,
    EffectType.state_module_diyu,
]
_MODULE_NAMES: Dict[EffectType, str] = {
    EffectType.state_module_qianghua: "强化模块",
    EffectType.state_module_jisu: "急速模块",
    EffectType.state_module_diyu: "抵御模块",
}
SHIELD_NAME = "防火墙"


class JifangfangLogic(SpiritLogic):
    template_id = TEMPLATE_ID
    SKILLS: ClassVar[Dict[str, str]] = {
        SKILL_FANGHUOQIANG: "_skill_fanghuoqiang",
        SKILL_BIANXIE: "_skill_bianxie",
        SKILL_CHAOXIAN: "_skill_chaoxian",
    }

    # --- 生命周期 ---

    def on_battle_start(self, ctx: BattleContext, spirit: BattleSpirit) -> None:
        if spirit.template_id != TEMPLATE_ID:
            return
        if not any(e.type in _MODULE_ORDER for e in spirit.effects):
            spirit.effects.append(
                make_effect(
                    EffectType.state_module_qianghua,
                    spirit.unique_id,
                    display_name=_MODULE_NAMES[EffectType.state_module_qianghua],
                )
            )
        ctx.add_log(
            BattleLogType.passive_triggered,
            msg.effect_gained(spirit.name, "强化模块"),
            {"sourceId": spirit.unique_id, "targetId": spirit.unique_id},
        )

    def _module_active(self, source: BattleSpirit, module: EffectType) -> bool:
        return any(
            e.type == module or e.type == EffectType.state_module_chaoxian
            for e in source.effects
        )

    # --- 模块光环（作用于持有本方方护盾的己方目标）---

    def get_aura_stat_percent_bonus(
        self,
        ctx: BattleContext,
        source: BattleSpirit,
        target: BattleSpirit,
        stat: StatType,
    ) -> float:
        if source.template_id != TEMPLATE_ID or stat != StatType.speed:
            return 0.0
        if not source.is_alive or not has_shield_from(target, source.unique_id):
            return 0.0
        return (
            MODULE_SPEED_BONUS
            if self._module_active(source, EffectType.state_module_jisu)
            else 0.0
        )

    def get_aura_damage_percent_bonus(
        self,
        ctx: BattleContext,
        source: BattleSpirit,
        spirit: BattleSpirit,
    ) -> float:
        if source.template_id != TEMPLATE_ID or not source.is_alive:
            return 0.0
        if not has_shield_from(spirit, source.unique_id):
            return 0.0
        return (
            MODULE_DAMAGE_BONUS
            if self._module_active(source, EffectType.state_module_qianghua)
            else 0.0
        )

    def get_aura_taken_damage_reduction(
        self,
        ctx: BattleContext,
        source: BattleSpirit,
        spirit: BattleSpirit,
    ) -> float:
        if source.template_id != TEMPLATE_ID or not source.is_alive:
            return 0.0
        if not has_shield_from(spirit, source.unique_id):
            return 0.0
        return (
            MODULE_TAKEN_REDUCTION
            if self._module_active(source, EffectType.state_module_diyu)
            else 0.0
        )

    def on_action_end(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
        *,
        stunned: bool,
    ) -> None:
        if actor.template_id != TEMPLATE_ID or stunned:
            return
        # 多色模块：使用技能后轮转（普通攻击 / 聚能不触发）。
        if not action.get("skillId"):
            return
        self._rotate_module(ctx, actor)

    def _rotate_module(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        current = next((e for e in actor.effects if e.type in _MODULE_ORDER), None)
        if current is None:
            nxt = EffectType.state_module_qianghua
        else:
            idx = _MODULE_ORDER.index(current.type)
            nxt = _MODULE_ORDER[(idx + 1) % len(_MODULE_ORDER)]
            actor.effects.remove(current)
        actor.effects.append(
            make_effect(nxt, actor.unique_id, display_name=_MODULE_NAMES[nxt])
        )
        ctx.add_log(
            BattleLogType.passive_triggered,
            msg.effect_gained(actor.name, _MODULE_NAMES[nxt]),
            {"sourceId": actor.unique_id, "targetId": actor.unique_id},
        )

    # --- 技能 ---

    def _grant_wall(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        target: BattleSpirit,
        ratio: float,
        cap_ratio: float,
        duration: int,
    ) -> int:
        atk = get_effective_stat(actor, StatType.atk)
        return grant_shield(
            target,
            actor.unique_id,
            atk * ratio,
            atk * cap_ratio,
            duration=duration,
            display_name=SHIELD_NAME,
        )

    def _skill_fanghuoqiang(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del action
        for ally in ctx.get_active_spirits(player_id):
            self._grant_wall(
                ctx, actor, ally, FANGHUOQIANG_RATIO, FANGHUOQIANG_CAP_RATIO, FANGHUOQIANG_DURATION
            )
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.effect_gained(actor.name, "防火墙"),
            {"sourceId": actor.unique_id, "targetId": actor.unique_id},
        )

    def _skill_bianxie(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_ally(ctx, player_id, action.get("targetId"))
        if not target:
            return
        gained = self._grant_wall(
            ctx, actor, target, BIANXIE_RATIO, BIANXIE_CAP_RATIO, BIANXIE_DURATION
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.shield_gain(target.name, "防火墙", source=actor.name),
            {"sourceId": actor.unique_id, "targetId": target.unique_id},
        )

    def _skill_chaoxian(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id, action
        existing = next(
            (e for e in actor.effects if e.type == EffectType.state_module_chaoxian), None
        )
        if existing is not None:
            existing.duration_turns = CHAOXIAN_DURATION
        else:
            actor.effects.append(
                make_effect(
                    EffectType.state_module_chaoxian,
                    actor.unique_id,
                    duration_turns=CHAOXIAN_DURATION,
                    display_name="超限模块",
                )
            )
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.effect_gained(actor.name, "超限模块"),
            {"sourceId": actor.unique_id, "targetId": actor.unique_id},
        )


jifangfang_logic = JifangfangLogic()
