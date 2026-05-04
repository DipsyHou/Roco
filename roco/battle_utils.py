"""Damage formulas, stats, effects — ported from TS battleUtils."""

from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from .battle_types import (
    BaseStats,
    BattleEffect,
    BattleSpirit,
    DamageModifySubType,
    DamageType,
    EffectType,
    StatType,
)


def _stat_base(spirit: BattleSpirit, stat: StatType) -> int:
    bs = spirit.base_stats
    if stat == StatType.hp:
        return bs.hp
    if stat == StatType.atk:
        return bs.atk
    if stat == StatType.mag_atk:
        return bs.mag_atk
    if stat == StatType.def_:
        return bs.def_
    if stat == StatType.mag_def:
        return bs.mag_def
    if stat == StatType.speed:
        return bs.speed
    return 0


def get_effective_stat(spirit: BattleSpirit, stat: StatType) -> int:
    if stat == StatType.hp:
        return spirit.max_hp

    base = _stat_base(spirit, stat)
    percent_sum = 0.0
    flat_sum = 0.0

    for eff in spirit.effects:
        if eff.stat_type != stat:
            continue
        if eff.type == EffectType.stat_percent_modify and eff.value is not None:
            percent_sum += eff.value
        if eff.type == EffectType.stat_flat_modify and eff.value is not None:
            flat_sum += eff.value

    result = base * (1 + percent_sum) + flat_sum
    return max(0, int(result))


def get_effective_speed(spirit: BattleSpirit) -> int:
    return get_effective_stat(spirit, StatType.speed)


def get_damage_modifiers(spirit: BattleSpirit) -> Tuple[float, float, float, float]:
    physical_increase = 0.0
    magical_increase = 0.0
    physical_decrease = 0.0
    magical_decrease = 0.0

    for eff in spirit.effects:
        if eff.type != EffectType.damage_modify or eff.value is None:
            continue
        sub = eff.damage_modify_sub_type
        v = eff.value
        if sub == DamageModifySubType.physical_increase:
            physical_increase += v
        elif sub == DamageModifySubType.magical_increase:
            magical_increase += v
        elif sub == DamageModifySubType.physical_decrease:
            physical_decrease += v
        elif sub == DamageModifySubType.magical_decrease:
            magical_decrease += v
        elif sub == DamageModifySubType.all_increase:
            physical_increase += v
            magical_increase += v
        elif sub == DamageModifySubType.all_decrease:
            physical_decrease += v
            magical_decrease += v

    return physical_increase, magical_increase, physical_decrease, magical_decrease


def calculate_damage(
    raw_damage: float,
    damage_type: DamageType,
    attacker: BattleSpirit,
    defender: BattleSpirit,
) -> int:
    if damage_type == DamageType.fixed:
        return max(0, int(raw_damage))

    def_val = (
        get_effective_stat(defender, StatType.def_)
        if damage_type == DamageType.physical
        else get_effective_stat(defender, StatType.mag_def)
    )

    base_dmg = (raw_damage * 100 / def_val) if def_val > 0 else raw_damage * 100

    att_pi, att_mi, _, _ = get_damage_modifiers(attacker)
    _, _, def_pd, def_md = get_damage_modifiers(defender)

    increase_rate = att_pi if damage_type == DamageType.physical else att_mi
    decrease_rate = def_pd if damage_type == DamageType.physical else def_md

    chaos_reduction = 0.0
    if defender.template_id == "chaosling":
        debuff_count = sum(1 for e in defender.effects if e.is_debuff)
        chaos_reduction = min(0.1, debuff_count * 0.02)

    final_dmg = base_dmg * (1 + increase_rate) * (1 - decrease_rate) * (1 - chaos_reduction)

    next_red = next((e for e in defender.effects if e.type == EffectType.next_damage_reduction), None)
    if next_red and next_red.reduction_percent is not None:
        final_dmg *= 1 - next_red.reduction_percent

    return max(0, int(final_dmg))


def is_stunned(spirit: BattleSpirit) -> bool:
    return any(e.type == EffectType.stun for e in spirit.effects)


def is_debuff_immune(spirit: BattleSpirit) -> bool:
    return any(e.type == EffectType.debuff_immunity for e in spirit.effects)


def make_effect(
    eff_type: EffectType,
    source_id: str,
    remaining_turns: int,
    is_debuff: bool,
    *,
    stat_type: Optional[StatType] = None,
    value: Optional[float] = None,
    damage_modify_sub_type: Optional[DamageModifySubType] = None,
    reduction_percent: Optional[float] = None,
    enhance_type: Optional[str] = None,
    magic_damage_ratio: Optional[float] = None,
    channel_phase: Optional[int] = None,
    channel_skill_id: Optional[str] = None,
) -> BattleEffect:
    return BattleEffect(
        id=str(uuid.uuid4()),
        type=eff_type,
        source_id=source_id,
        remaining_turns=remaining_turns,
        is_debuff=is_debuff,
        stat_type=stat_type,
        value=value,
        damage_modify_sub_type=damage_modify_sub_type,
        reduction_percent=reduction_percent,
        enhance_type=enhance_type,
        magic_damage_ratio=magic_damage_ratio,
        channel_phase=channel_phase,
        channel_skill_id=channel_skill_id,
    )


def apply_damage(spirit: BattleSpirit, damage: int) -> int:
    actual = min(spirit.current_hp, damage)
    spirit.current_hp -= actual
    if spirit.current_hp <= 0:
        spirit.current_hp = 0
        spirit.is_alive = False
        spirit.is_on_field = False
    return actual


def apply_heal(spirit: BattleSpirit, amount: float) -> int:
    actual = min(spirit.max_hp - spirit.current_hp, int(amount))
    spirit.current_hp += actual
    return actual


def purge_debuffs(spirit: BattleSpirit) -> List[BattleEffect]:
    removed = [e for e in spirit.effects if e.is_debuff]
    spirit.effects = [e for e in spirit.effects if not e.is_debuff]
    return removed


def consume_next_damage_reduction(spirit: BattleSpirit) -> None:
    idx = next((i for i, e in enumerate(spirit.effects) if e.type == EffectType.next_damage_reduction), None)
    if idx is not None:
        spirit.effects.pop(idx)


def tick_effects(spirit: BattleSpirit) -> List[BattleEffect]:
    expired: List[BattleEffect] = []
    kept: List[BattleEffect] = []

    for eff in spirit.effects:
        if eff.remaining_turns == -1:
            kept.append(eff)
            continue
        eff.remaining_turns -= 1
        if eff.remaining_turns <= 0:
            expired.append(eff)
        else:
            kept.append(eff)

    spirit.effects = kept
    return expired
