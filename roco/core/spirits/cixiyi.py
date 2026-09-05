"""石化刺蜥蜴 — 硬化肌肤 / 看破棘皮 / 再生 / 岩刺。

- 硬化肌肤（被动）：受到的固定伤害降低 50%（开局挂一条永久的固伤减免效果）。
- 棘皮（技能）：给全体己方挂「棘皮」标记；持有者「受到伤害后」移除标记并获得
  （30% 施加者物防）护盾，上限（60% 施加者物防），持续 3 回合，可累积刷新。
- 再生（被动）：自身受到伤害后 +20% 双防、并使「棘皮」能耗 −2，持续 1 回合，
  再次获得延长 1 回合，最多 2 回合。
- 岩刺（技能）：对自身造成（20% 物攻）物理伤害，再对目标造成
  （120% 自身物防 + 100% 自身护盾量）物理伤害。

「受到伤害后」类触发统一走 ``on_damage`` 观察者：石化刺蜥蜴存活时即可为全队的
「棘皮」结算（护盾也算受到伤害，见 docs/mechanics.md §22.3）。
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List

from ..battle import messages as msg
from ..battle.events import DamageEvent, DamageSource
from ..battle.shield import grant_shield, total_shield
from ..battle.types import (
    BattleLogType,
    BattleSpirit,
    DamageType,
    EffectType,
    StatType,
)
from ..battle.utils import get_effective_stat, make_effect
from ._combat import deal_atk_ratio, deal_damage, target_enemy
from ..spirit_logic import BattleContext, SpiritLogic

TEMPLATE_ID = "cixiyi"

HARDEN_FIXED_REDUCTION = 0.5
JIPI_SHIELD_RATIO = 0.30
JIPI_SHIELD_CAP_RATIO = 0.60
JIPI_SHIELD_DURATION = 3
ZAISHENG_DEF_BONUS = 0.20
ZAISHENG_COST_REDUCTION = 2
ZAISHENG_MAX_DURATION = 2
YANCI_SELF_RATIO = 0.20
YANCI_DEF_RATIO = 1.20
YANCI_SHIELD_RATIO = 1.00

SKILL_JIPI = "cixiyi_skill1"
SKILL_YANCI = "cixiyi_skill2"


def _has(spirit: BattleSpirit, eff_type: EffectType) -> bool:
    return any(e.type == eff_type for e in spirit.effects)


class CixiyiLogic(SpiritLogic):
    template_id = TEMPLATE_ID
    SKILLS: ClassVar[Dict[str, str]] = {
        SKILL_JIPI: "_skill_jipi",
        SKILL_YANCI: "_skill_yanci",
    }

    # --- 生命周期 ---

    def on_battle_start(self, ctx: BattleContext, spirit: BattleSpirit) -> None:
        if spirit.template_id != TEMPLATE_ID:
            return
        if not _has(spirit, EffectType.state_yinghuajifu):
            spirit.effects.append(
                make_effect(
                    EffectType.state_yinghuajifu,
                    spirit.unique_id,
                    display_name="硬化肌肤",
                )
            )
        ctx.add_log(
            BattleLogType.passive_triggered,
            msg.passive(spirit.name, "硬化肌肤"),
            msg.data_effect(spirit.unique_id, spirit.unique_id),
        )

    def get_incoming_damage_reduction(
        self, spirit: BattleSpirit, damage_type: DamageType
    ) -> float:
        if spirit.template_id != TEMPLATE_ID or damage_type != DamageType.fixed:
            return 0.0
        return HARDEN_FIXED_REDUCTION if _has(spirit, EffectType.state_yinghuajifu) else 0.0

    # --- 能力值 / 能耗（再生）---

    def get_stat_percent_bonus(self, spirit: BattleSpirit, stat: StatType) -> float:
        if spirit.template_id != TEMPLATE_ID:
            return 0.0
        if stat in (StatType.def_, StatType.mag_def) and _has(spirit, EffectType.state_zaisheng):
            return ZAISHENG_DEF_BONUS
        return 0.0

    def get_skill_energy_cost(self, spirit: BattleSpirit, skill, base_cost: int) -> int:
        if (
            spirit.template_id == TEMPLATE_ID
            and skill.id == SKILL_JIPI
            and _has(spirit, EffectType.state_zaisheng)
        ):
            return max(0, base_cost - ZAISHENG_COST_REDUCTION)
        return base_cost

    # --- 受击触发：棘皮转盾 + 再生 ---

    def on_damage(self, ctx: BattleContext, spirit: BattleSpirit, event: DamageEvent) -> None:
        if spirit.template_id != TEMPLATE_ID or event.damage <= 0:
            return
        target = event.target
        # 棘皮：由本蜥蜴施加的「棘皮」在持有者受击后转化为护盾
        jipi = next(
            (
                e
                for e in target.effects
                if e.type == EffectType.state_jipi and e.source_id == spirit.unique_id
            ),
            None,
        )
        if jipi is not None and target.is_alive:
            target.effects.remove(jipi)
            def_val = get_effective_stat(spirit, StatType.def_)
            gained = grant_shield(
                target,
                spirit.unique_id,
                def_val * JIPI_SHIELD_RATIO,
                def_val * JIPI_SHIELD_CAP_RATIO,
                duration=JIPI_SHIELD_DURATION,
                display_name="棘皮护盾",
            )
            ctx.add_log(
                BattleLogType.effect_applied,
                msg.effect_gained(target.name, "棘皮护盾"),
                msg.data_effect(target.unique_id, spirit.unique_id),
            )
        # 再生：自身受击后加防减费
        if target.unique_id == spirit.unique_id and spirit.is_alive:
            self._refresh_zaisheng(ctx, spirit)

    def _refresh_zaisheng(self, ctx: BattleContext, spirit: BattleSpirit) -> None:
        existing = next(
            (e for e in spirit.effects if e.type == EffectType.state_zaisheng), None
        )
        if existing is None:
            spirit.effects.append(
                make_effect(
                    EffectType.state_zaisheng,
                    spirit.unique_id,
                    duration_turns=1,
                    display_name="再生",
                )
            )
        else:
            existing.duration_turns = min(
                ZAISHENG_MAX_DURATION, (existing.duration_turns or 0) + 1
            )
        ctx.add_log(
            BattleLogType.passive_triggered,
            msg.passive(spirit.name, "再生"),
            msg.data_effect(spirit.unique_id, spirit.unique_id),
        )

    # --- 技能 ---

    def _skill_jipi(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del action
        applied = False
        for ally in ctx.get_active_spirits(player_id):
            if any(e.type == EffectType.state_jipi for e in ally.effects):
                continue
            ally.effects.append(
                make_effect(
                    EffectType.state_jipi,
                    actor.unique_id,
                    display_name="棘皮",
                )
            )
            applied = True
        if applied:
            ctx.add_log(
                BattleLogType.effect_applied,
                msg.effect_gained(actor.name, "棘皮"),
                msg.data_effect(actor.unique_id, actor.unique_id),
            )

    def _skill_yanci(
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
            actor,
            YANCI_SELF_RATIO,
            lambda a: msg.skill_damage(actor.name, "岩刺", actor.name, a),
            source=DamageSource.other,
        )
        if not actor.is_alive or not target.is_alive:
            return
        def_val = get_effective_stat(actor, StatType.def_)
        raw = def_val * YANCI_DEF_RATIO + total_shield(actor) * YANCI_SHIELD_RATIO
        deal_damage(
            ctx,
            actor,
            target,
            raw,
            DamageType.physical,
            lambda a: msg.skill_damage(actor.name, "岩刺", target.name, a),
            source=DamageSource.skill,
            crit_rng=ctx.next_rng("cixiyi_yanci_crit", actor.unique_id, target.unique_id),
        )


cixiyi_logic = CixiyiLogic()
