"""小琮 — 技能 & 被动（灵气 / 灵珏护体 / 通灵）"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, Optional

from ..battle.types import (
    BattleLogType,
    BattleSpirit,
    DamageType,
    EffectType,
    StatType,
)
from ..battle.utils import (
    apply_heal,
    get_effective_stat,
    make_effect,
)
from ._combat import deal_damage, target_enemy
from ..spirit_logic import BattleContext, DamageSource, SpiritLogic

TEMPLATE_ID = "xiaozong"
TONGLING_COST = 30
LINGQI_PER_SKILL = 30
SKILL_COST_REDUCTION_LABELS = {
    "xiaozong_skill1": "日月齐光能耗降低1点",
    "xiaozong_skill2": "华采若英能耗降低1点",
}
YUANJU_MITIGATION_TAG = "xiaozong_yuanju_mitigation"


def _lingqi_cap(spirit: BattleSpirit) -> int:
    return spirit.battle_start_max_hp or spirit.max_hp


def _get_lingqi_effect(spirit: BattleSpirit):
    return next(
        (e for e in spirit.effects if e.type == EffectType.state_lingqi),
        None,
    )


def get_lingqi_stacks(spirit: BattleSpirit) -> int:
    eff = _get_lingqi_effect(spirit)
    return max(0, eff.stacks) if eff else 0


def add_lingqi(spirit: BattleSpirit, amount: int) -> None:
    if amount <= 0:
        return
    cap = _lingqi_cap(spirit)
    eff = _get_lingqi_effect(spirit)
    if eff:
        eff.stacks = min(cap, eff.stacks + amount)
    else:
        spirit.effects.append(
            make_effect(
                EffectType.state_lingqi,
                spirit.unique_id,
                stacks=min(cap, amount),
            )
        )


def consume_lingqi(spirit: BattleSpirit, amount: int) -> None:
    eff = _get_lingqi_effect(spirit)
    if not eff:
        return
    eff.stacks -= amount
    if eff.stacks <= 0:
        spirit.effects = [e for e in spirit.effects if e.type != EffectType.state_lingqi]


def clear_lingqi(spirit: BattleSpirit) -> None:
    spirit.effects = [e for e in spirit.effects if e.type != EffectType.state_lingqi]


def has_tongling(spirit: BattleSpirit) -> bool:
    return any(e.type == EffectType.state_tongling for e in spirit.effects)


def grant_tongling(spirit: BattleSpirit) -> None:
    if not has_tongling(spirit):
        spirit.effects.append(
            make_effect(EffectType.state_tongling, spirit.unique_id)
        )


class XiaozongLogic(SpiritLogic):
    template_id = TEMPLATE_ID
    SKILLS: ClassVar[Dict[str, str]] = {
        "xiaozong_skill1": "_skill_riyue",
        "xiaozong_skill2": "_skill_huacai",
        "xiaozong_skill3": "_skill_yuanju",
    }

    def on_unit_created(self, spirit: BattleSpirit) -> None:
        spirit.battle_start_max_hp = spirit.max_hp

    def apply_passive_flat_mitigation(self, spirit: BattleSpirit, damage: float) -> float:
        cap = int(get_lingqi_stacks(spirit) * 0.1)
        if cap <= 0:
            return damage
        applied = min(cap, max(0, damage))
        if not has_tongling(spirit) and applied > 0:
            add_lingqi(spirit, applied)
        return max(0, damage - applied)

    def on_death(
        self,
        spirit: BattleSpirit,
        ctx: Optional[BattleContext] = None,
    ) -> bool:
        if has_tongling(spirit):
            return False
        stacks = get_lingqi_stacks(spirit)
        if stacks <= 0:
            return False
        spirit.current_hp = min(stacks, spirit.max_hp)
        spirit.is_alive = True
        grant_tongling(spirit)
        if ctx is not None:
            ctx.add_log(
                BattleLogType.passive_triggered,
                f"{spirit.name} 的灵珏御光触发！通灵将其生命续至 {spirit.current_hp} 点！",
                {"targetId": spirit.unique_id},
            )
        return True

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
        if self._enter_tongling_mode(actor):
            self._hit(
                ctx, actor, target,
                get_effective_stat(actor, StatType.mag_atk) * 1.0,
                DamageType.magical, "普通攻击", source=DamageSource.attack,
            )
        else:
            self._hit(
                ctx, actor, target,
                get_effective_stat(actor, StatType.atk) * 1.0,
                DamageType.physical, "普通攻击", source=DamageSource.attack,
            )
        return True

    def _hit(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        target: BattleSpirit,
        raw: float,
        damage_type: DamageType,
        verb: str,
        source: DamageSource = DamageSource.skill,
    ) -> int:
        type_label = "物理" if damage_type == DamageType.physical else "魔法"
        return deal_damage(
            ctx,
            actor,
            target,
            raw,
            damage_type,
            lambda a: f"{actor.name} 的{verb}对 {target.name} 造成了 {a} 点{type_label}伤害！",
            source=source,
        )

    def _skill_riyue(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        mag = get_effective_stat(actor, StatType.mag_atk)
        tongling = self._enter_tongling_mode(actor)
        main_ratio = 1.20 if tongling else 0.80
        adj_ratio = 0.60 if tongling else 0.40
        self._hit(ctx, actor, target, mag * main_ratio, DamageType.magical, "日月齐光")
        for adj in ctx.get_adjacent_enemies(target):
            if adj.is_alive:
                self._hit(ctx, actor, adj, mag * adj_ratio, DamageType.magical, "日月齐光")
        if not tongling:
            self._grant_lingqi(ctx, actor, LINGQI_PER_SKILL)

    def _skill_huacai(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        mag = get_effective_stat(actor, StatType.mag_atk)
        stacks_at_cast = get_lingqi_stacks(actor)
        tongling = self._enter_tongling_mode(actor)
        raw = mag * 0.80 + stacks_at_cast * 0.20
        dealt = self._hit(ctx, actor, target, raw, DamageType.magical, "华采若英")
        if tongling:
            heal = int(dealt * 0.30)
            if heal > 0:
                actual = apply_heal(actor, heal)
                if actual > 0:
                    ctx.add_log(
                        BattleLogType.heal_applied,
                        f"{actor.name} 凭华采若英回复了 {actual} 点血量！",
                        {"targetId": actor.unique_id, "heal": actual},
                    )
        else:
            self._grant_lingqi(ctx, actor, LINGQI_PER_SKILL)

    def _skill_yuanju(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id, action
        tongling = self._enter_tongling_mode(actor)
        reduction = 0.15 if tongling else 0.10
        self._apply_mitigation_reduction(actor, reduction)
        self._apply_cost_reduction(actor)
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 获得了 {int(reduction * 100)}% 减伤，日月齐光与华采若英能量消耗降低1点",
            {"targetId": actor.unique_id},
        )
        if not tongling:
            self._grant_lingqi(ctx, actor, LINGQI_PER_SKILL)

    def _enter_tongling_mode(self, actor: BattleSpirit) -> bool:
        if not has_tongling(actor):
            return False
        stacks = get_lingqi_stacks(actor)
        if stacks >= TONGLING_COST:
            consume_lingqi(actor, TONGLING_COST)
        elif stacks > 0:
            clear_lingqi(actor)
        return True

    def _grant_lingqi(self, ctx: BattleContext, actor: BattleSpirit, amount: int) -> None:
        add_lingqi(actor, amount)
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 凝聚了 {amount} 层灵气",
            {"targetId": actor.unique_id},
        )

    def _apply_mitigation_reduction(self, actor: BattleSpirit, reduction: float) -> None:
        existing = next(
            (
                e
                for e in actor.effects
                if e.type == EffectType.buff_taken_damage_percent_reduction
                and e.effect_tag == YUANJU_MITIGATION_TAG
            ),
            None,
        )
        if existing:
            existing.duration_turns = 3
            existing.value = reduction
        else:
            actor.effects.append(
                make_effect(
                    EffectType.buff_taken_damage_percent_reduction,
                    actor.unique_id,
                    duration_turns=3,
                    value=reduction,
                    effect_tag=YUANJU_MITIGATION_TAG,
                )
            )

    def _apply_cost_reduction(self, actor: BattleSpirit) -> None:
        for skill_id, label in SKILL_COST_REDUCTION_LABELS.items():
            existing = next(
                (
                    e
                    for e in actor.effects
                    if e.type == EffectType.buff_skill_energy_cost_reduction
                    and e.effect_tag == skill_id
                ),
                None,
            )
            if existing:
                existing.duration_turns = 3
                existing.value = 1
                existing.display_name = label
            else:
                actor.effects.append(
                    make_effect(
                        EffectType.buff_skill_energy_cost_reduction,
                        actor.unique_id,
                        duration_turns=3,
                        value=1,
                        effect_tag=skill_id,
                        display_name=label,
                    )
                )


xiaozong_logic = XiaozongLogic()
