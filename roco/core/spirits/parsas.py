"""帕尔萨斯 — 收藏灵魂 / 恶魔契约 / 巨魔之眼 / 新月乱舞

秘能机制说明：
- 秘能上限 20，开局 2 点；成为普攻/技能唯一目标时 +2（含自身技能）；普攻命中 +1。
- 被动是**边沿触发**：只有秘能从 <13 越过到 >=13 的那一刻才提前 100%，
  并若已有「恐怖」则延长 1 回合；持续停留在线以上不会重复触发。
- 恐怖（buff_def_pierce，魔法）不修改目标的真实防御值，只在结算魔法伤害时让
  魔防被视为按穿透百分点降低，实现见 ``roco/core/battle/damage.py``。
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, Optional

from ..battle import messages as msg
from ..battle import messages as msg
from ..battle.types import BattleLogType, BattleSpirit, DamageType, EffectType
from ..battle.utils import make_effect
from ._combat import deal_atk_ratio, deal_mag_ratio, grant_personal_energy, target_enemy
from ..spirit_logic import BattleContext, SpiritLogic

ENERGY_CAP = 20
ENERGY_THRESHOLD = 13
OPENING_ENERGY = 2
SOLE_TARGET_ENERGY = 2
CONTRACT_HP_RATIO = 0.10
CONTRACT_ENERGY_GAIN = 3
TROLL_ENERGY_COST = 7
TROLL_ATK_RATIO = 1.20
TERROR_DURATION = 3
TERROR_DEF_PIERCE = 0.10
TERROR_EXTEND_ON_THRESHOLD = 1
MOON_ENERGY_COST = 13
MOON_MAIN_ATK_RATIO = 1.20
MOON_AOE_ATK_RATIO = 0.80


class ParsasLogic(SpiritLogic):
    template_id = "parsas"
    SKILLS: ClassVar[Dict[str, str]] = {
        "parsas_skill1": "_skill_contract",
        "parsas_skill2": "_skill_troll_eye",
        "parsas_skill3": "_skill_crescent_dance",
    }

    # --- 秘能：授予入口，边沿检测 ---

    def on_unit_created(self, spirit: BattleSpirit) -> None:
        # 开局秘能在 on_battle_start 经统一入口发放，以便吃到圣域祭司月盈。
        spirit.energy = 0
        spirit.max_energy = ENERGY_CAP

    def on_battle_start(self, ctx: BattleContext, spirit: BattleSpirit) -> None:
        self._grant_energy(ctx, spirit, OPENING_ENERGY)

    def get_resource_label(self) -> Optional[str]:
        """帕尔萨斯用个人秘能付费，技能固定不消耗队伍能量。"""
        return "秘能"

    def should_use_team_energy(self, spirit: BattleSpirit, skill) -> bool:
        return False

    def _grant_energy(self, ctx: BattleContext, spirit: BattleSpirit, amount: int) -> int:
        """授予秘能并检测跨线；返回实际获得量。

        跨线检测比较授予前后的值：只有「之前 < 13 且之后 >= 13」才触发提前，
        持续停留在线以上（例如再获得更多秘能）不会重复触发。授予走
        ``grant_personal_energy``，会叠加队友秘能放大（如圣域祭司月盈）。
        """
        if amount <= 0 or spirit.template_id != self.template_id:
            return 0
        before = spirit.energy or 0
        gained = grant_personal_energy(ctx, spirit, amount)
        after = spirit.energy or 0
        if before < ENERGY_THRESHOLD <= after:
            ctx.advance_action(spirit, 1.0)
            terror = next(
                (e for e in spirit.effects if e.type == EffectType.buff_def_pierce),
                None,
            )
            if terror is not None and terror.duration_turns is not None:
                terror.duration_turns += TERROR_EXTEND_ON_THRESHOLD
            ctx.add_log(
                BattleLogType.passive_triggered,
                msg.passive(spirit.name, "收藏灵魂"),
                {"actorId": spirit.unique_id},
            )
        return gained

    def on_ally_turn_start(
        self,
        ctx: BattleContext,
        player_id: str,
        observer: BattleSpirit,
        actor: BattleSpirit,
    ) -> None:
        del ctx, player_id, observer, actor

    def on_became_sole_target(
        self,
        ctx: BattleContext,
        spirit: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del action
        if spirit.template_id != self.template_id or not spirit.is_alive:
            return
        self._grant_energy(ctx, spirit, SOLE_TARGET_ENERGY)

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
        self._grant_energy(ctx, actor, 1)
        actor.last_attack_target_id = target.unique_id
        return True

    # --- 技能 ---

    def can_use_skill(self, spirit: BattleSpirit, skill) -> Optional[tuple]:
        if skill.id == "parsas_skill2" and (spirit.energy or 0) < TROLL_ENERGY_COST:
            return (False, f"需要{TROLL_ENERGY_COST}点秘能")
        if skill.id == "parsas_skill3" and (spirit.energy or 0) < MOON_ENERGY_COST:
            return (False, f"需要{MOON_ENERGY_COST}点秘能")
        return (True, "")

    def _skill_contract(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id, action
        cost = int(actor.current_hp * CONTRACT_HP_RATIO)
        if cost > 0:
            actor.current_hp -= cost
            ctx.add_log(
                BattleLogType.damage_dealt,
                msg.hp_cost(actor.name, cost, skill="恶魔契约"),
                msg.data_hp_cost(actor.unique_id, cost),
            )
        self._grant_energy(ctx, actor, CONTRACT_ENERGY_GAIN)

    def _skill_troll_eye(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        actor.energy = max(0, (actor.energy or 0) - TROLL_ENERGY_COST)

        existing = next(
            (e for e in actor.effects if e.type == EffectType.buff_def_pierce), None
        )
        if existing:
            existing.duration_turns = TERROR_DURATION
            existing.damage_type = DamageType.magical
            existing.value = TERROR_DEF_PIERCE
        else:
            actor.effects.append(
                make_effect(
                    EffectType.buff_def_pierce,
                    actor.unique_id,
                    damage_type=DamageType.magical,
                    value=TERROR_DEF_PIERCE,
                    duration_turns=TERROR_DURATION,
                    display_name="恐怖",
                )
            )
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.effect_gained(actor.name, "恐怖"),
            msg.data_effect(actor.unique_id, actor.unique_id),
        )

        deal_mag_ratio(
            ctx,
            actor,
            target,
            TROLL_ATK_RATIO,
            lambda a: msg.skill_damage(
                actor.name, "巨魔之眼", target.name, a, kind=msg.KIND_MAGICAL
            ),
        )

    def _skill_crescent_dance(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        actor.energy = max(0, (actor.energy or 0) - MOON_ENERGY_COST)

        deal_mag_ratio(
            ctx,
            actor,
            target,
            MOON_MAIN_ATK_RATIO,
            lambda a: msg.skill_damage(
                actor.name, "新月乱舞", target.name, a, kind=msg.KIND_MAGICAL
            ),
        )

        opponent_id = ctx.get_opponent_id(player_id)
        for enemy in ctx.get_active_spirits(opponent_id):
            deal_mag_ratio(
                ctx,
                actor,
                enemy,
                MOON_AOE_ATK_RATIO,
                lambda a, t=enemy: msg.skill_damage(
                    actor.name, "新月乱舞", t.name, a, kind=msg.KIND_MAGICAL
                ),
            )


parsas_logic = ParsasLogic()
