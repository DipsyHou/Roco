"""圣域祭司 — 月盈 / 圣洁 / 指引 / 再现

秘能机制说明：
- 秘能上限 5，回合开始满值 5 点；回合结束消耗全部秘能换速度（每点 20 速，2回合）。
- 「己方精灵获得秘能后，使其额外获得1点秘能」通过 ``get_ally_energy_gain_bonus``
  接入通用入口 ``_combat.grant_personal_energy``：任何调用该入口授予秘能的精灵
  （帕尔萨斯、黑猫巫师等）在场上有本精灵时都会多得1点。圣域祭司自身的秘能是
  回合制满-清空，不经过该入口，不吃这条加成。
- 「再现」的复制目标类型：debuff_stat_percent_reduction / debuff_stat_flat_reduction
  （能力值降低，百分比或固定值）、debuff_damage_percent_reduction /
  debuff_damage_flat_reduction（造成伤害降低）、debuff_taken_damage_percent_boost /
  debuff_taken_damage_flat_boost（受到伤害提高）。复制出的效果打上
  ``effect_tag=COPY_TAG`` 标记，防止被二次复制；显示层由 ``effect_display.py``
  追加「(复制)」后缀。
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, Optional

from ..battle.types import BattleEffect, BattleLogType, BattleSpirit, EffectType, StatType
from ..battle.utils import apply_heal, get_effective_stat, make_effect
from ._combat import grant_personal_energy, target_ally, target_enemy
from ..spirit_logic import BattleContext, SpiritLogic

SHENGYU_ENERGY_CAP = 5
SHENGYU_SPEED_PER_POINT = 20
BLESSING_ENERGY_COST = 2
BLESSING_HEAL_RATIO = 0.60
GUIDANCE_ENERGY_COST = 4
GUIDANCE_TAKEN_DAMAGE_BOOST = 0.16
GUIDANCE_DURATION = 3
SPEED_BUFF_DURATION = 2
REPLICATE_ENERGY_COST = 5

COPY_TAG = "shengyu_replicated"

_COPYABLE_TYPES = (
    EffectType.debuff_stat_percent_reduction,
    EffectType.debuff_stat_flat_reduction,
    EffectType.debuff_damage_percent_reduction,
    EffectType.debuff_damage_flat_reduction,
    EffectType.debuff_taken_damage_percent_boost,
    EffectType.debuff_taken_damage_flat_boost,
)


class ShengyuLogic(SpiritLogic):
    template_id = "shengyu"
    SKILLS: ClassVar[Dict[str, str]] = {
        "shengyu_skill1": "_skill_blessing",
        "shengyu_skill2": "_skill_guidance",
        "shengyu_skill3": "_skill_replicate",
    }

    # --- 秘能：回合制满-清空，不经过增益入口 ---

    def on_unit_created(self, spirit: BattleSpirit) -> None:
        spirit.energy = SHENGYU_ENERGY_CAP
        spirit.max_energy = SHENGYU_ENERGY_CAP

    def get_resource_label(self) -> Optional[str]:
        """圣域祭司用个人秘能付费，技能固定不消耗队伍能量。"""
        return "秘能"

    def should_use_team_energy(self, spirit: BattleSpirit, skill) -> bool:
        return False

    def on_turn_start(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        if actor.template_id != self.template_id:
            return
        actor.energy = SHENGYU_ENERGY_CAP

    def on_turn_end(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
        *,
        stunned: bool = False,
    ) -> None:
        if actor.template_id != self.template_id:
            return
        consumed = actor.energy or 0
        if consumed <= 0:
            return
        actor.energy = 0
        actor.effects.append(
            make_effect(
                EffectType.buff_stat_percent_boost,
                actor.unique_id,
                stat_type=StatType.speed,
                value=self._speed_bonus_ratio(actor, consumed),
                duration_turns=SPEED_BUFF_DURATION,
                display_name="月盈",
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 的月盈消耗{consumed}点秘能，速度提高{SHENGYU_SPEED_PER_POINT * consumed}点！",
            {"targetId": actor.unique_id},
        )

    def _speed_bonus_ratio(self, actor: BattleSpirit, consumed: int) -> float:
        """将「+N点速度」换算为对基础速度的百分比加成，以复用百分比buff管线。"""
        base_speed = actor.base_stats.speed or 1
        return (SHENGYU_SPEED_PER_POINT * consumed) / base_speed

    def get_ally_energy_gain_bonus(
        self, ctx: BattleContext, observer: BattleSpirit, gainer: BattleSpirit
    ) -> int:
        if observer.template_id != self.template_id or not observer.is_alive:
            return 0
        return 1

    # --- 技能 ---

    def _skill_blessing(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_ally(ctx, player_id, action.get("targetId"))
        if not target:
            return
        actor.energy = max(0, (actor.energy or 0) - BLESSING_ENERGY_COST)
        mag = get_effective_stat(actor, StatType.mag_atk)
        heal = apply_heal(target, mag * BLESSING_HEAL_RATIO)
        if heal > 0:
            ctx.add_log(
                BattleLogType.heal_applied,
                f"{actor.name} 的圣洁为 {target.name} 回复了 {heal} 点血量！",
                {"actorId": actor.unique_id, "targetId": target.unique_id, "heal": heal},
            )
        if target.energy is not None:
            gained = grant_personal_energy(ctx, target, 1)
            if gained > 0:
                ctx.add_log(
                    BattleLogType.effect_applied,
                    f"{target.name} 额外回复了{gained}点秘能！",
                    {"targetId": target.unique_id},
                )

    def _skill_guidance(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        actor.energy = max(0, (actor.energy or 0) - GUIDANCE_ENERGY_COST)
        target.effects.append(
            make_effect(
                EffectType.debuff_taken_damage_percent_boost,
                actor.unique_id,
                value=GUIDANCE_TAKEN_DAMAGE_BOOST,
                duration_turns=GUIDANCE_DURATION,
                display_name="指引",
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 的指引使 {target.name} 受到的伤害提高16%（3回合）！",
            {"targetId": target.unique_id, "sourceId": actor.unique_id},
        )

    def _skill_replicate(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        actor.energy = max(0, (actor.energy or 0) - REPLICATE_ENERGY_COST)

        candidates = [
            e
            for e in target.effects
            if e.type in _COPYABLE_TYPES and e.effect_tag != COPY_TAG
        ]
        if not candidates:
            ctx.add_log(
                BattleLogType.effect_applied,
                f"{actor.name} 消耗{REPLICATE_ENERGY_COST}点秘能施放了再现，但 {target.name} 没有可复制的负面效果。",
                {"targetId": target.unique_id},
            )
            return

        picked = ctx.next_rng("shengyu_replicate", actor.unique_id).choice(candidates)
        opponent_id = ctx.get_opponent_id(player_id)
        others = [s for s in ctx.get_active_spirits(opponent_id) if s.unique_id != target.unique_id]
        for other in others:
            other.effects.append(self._clone_effect(picked, other))

        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 的再现将 {target.name} 的一个负面效果复制给了敌方全体！",
            {"sourceId": actor.unique_id, "targetId": target.unique_id},
        )

    def _clone_effect(self, original: BattleEffect, new_target: BattleSpirit) -> BattleEffect:
        """按原效果的来源与数值克隆一份，打上复制标记以阻止二次复制。"""
        return make_effect(
            original.type,
            original.source_id,
            duration_turns=original.duration_turns,
            stacks=original.stacks,
            stat_type=original.stat_type,
            value=original.value,
            damage_type=original.damage_type,
            effect_tag=COPY_TAG,
            display_name=original.display_name,
        )


shengyu_logic = ShengyuLogic()
