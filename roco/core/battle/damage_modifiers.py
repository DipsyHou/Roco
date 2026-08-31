"""Damage modifier extraction helpers."""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional, Tuple

from .types import BattleSpirit, DamageType, EffectType

SUSTAINED_DAMAGE_TAG = "sustained_damage"


class DamageModifierMode(str, Enum):
    """Which percent modifiers apply during ``calculate_damage``."""

    normal = "normal"
    sustained_burn = "sustained_burn"
    sustained_poison = "sustained_poison"


def _is_sustained_tagged(effect) -> bool:
    return effect.effect_tag == SUSTAINED_DAMAGE_TAG


def _match_damage_type(
    eff_dt: Optional[DamageType],
    target_dt: DamageType,
) -> bool:
    """Normal-mode matching: ``None`` applies to physical and magical only."""
    if eff_dt is None:
        return target_dt in (DamageType.physical, DamageType.magical)
    return eff_dt == target_dt


def _outgoing_percent_applies(
    effect,
    damage_type: DamageType,
    mode: DamageModifierMode,
) -> bool:
    tagged = _is_sustained_tagged(effect)
    if mode == DamageModifierMode.sustained_burn:
        return tagged
    if mode == DamageModifierMode.sustained_poison:
        return False
    return not tagged and _match_damage_type(effect.damage_type, damage_type)


def _incoming_percent_applies(
    effect,
    damage_type: DamageType,
    mode: DamageModifierMode,
) -> bool:
    tagged = _is_sustained_tagged(effect)
    if mode == DamageModifierMode.sustained_burn:
        return tagged
    if mode == DamageModifierMode.sustained_poison:
        return not tagged and effect.damage_type == DamageType.fixed
    return not tagged and _match_damage_type(effect.damage_type, damage_type)


def get_damage_modifiers(
    spirit: BattleSpirit,
    damage_type: DamageType,
    mode: DamageModifierMode = DamageModifierMode.normal,
) -> Tuple[float, float, float, float, float, float]:
    """Attacker percent inc/dec by damage type."""
    pi = mi = fi = pd = md = fd = 0.0

    for effect in spirit.effects:
        if effect.value is None:
            continue
        if not _outgoing_percent_applies(effect, damage_type, mode):
            continue
        value = effect.value
        if mode == DamageModifierMode.sustained_burn:
            if damage_type != DamageType.physical:
                continue
            if effect.type == EffectType.buff_damage_percent_boost:
                pi += value
            elif effect.type == EffectType.debuff_damage_percent_reduction:
                pd += value
            continue
        if effect.type == EffectType.buff_damage_percent_boost:
            if _match_damage_type(effect.damage_type, damage_type):
                if damage_type == DamageType.physical:
                    pi += value
                elif damage_type == DamageType.magical:
                    mi += value
                elif damage_type == DamageType.fixed:
                    fi += value
        elif effect.type == EffectType.debuff_damage_percent_reduction:
            if _match_damage_type(effect.damage_type, damage_type):
                if damage_type == DamageType.physical:
                    pd += value
                elif damage_type == DamageType.magical:
                    md += value
                elif damage_type == DamageType.fixed:
                    fd += value

    return pi, mi, fi, pd, md, fd


def get_flat_damage_modifiers(
    spirit: BattleSpirit,
) -> Tuple[float, float, float, float, float, float]:
    """Deprecated: flat outgoing modifiers are no longer used."""
    return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0


def get_incoming_damage_modifiers(
    spirit: BattleSpirit,
    damage_type: DamageType,
    mode: DamageModifierMode = DamageModifierMode.normal,
) -> Tuple[float, float, float]:
    """Defender percent reductions by damage type; negative values increase damage."""
    pr = mr = fr = 0.0

    for effect in spirit.effects:
        if effect.value is None:
            continue
        if not _incoming_percent_applies(effect, damage_type, mode):
            continue
        value = effect.value
        if mode == DamageModifierMode.sustained_burn:
            if damage_type != DamageType.physical:
                continue
            if effect.type == EffectType.buff_taken_damage_percent_reduction:
                pr += value
            elif effect.type == EffectType.debuff_taken_damage_percent_boost:
                pr -= value
            continue
        if effect.type == EffectType.buff_taken_damage_percent_reduction:
            if _match_damage_type(effect.damage_type, damage_type):
                if damage_type == DamageType.physical:
                    pr += value
                elif damage_type == DamageType.magical:
                    mr += value
                elif damage_type == DamageType.fixed:
                    fr += value
        elif effect.type == EffectType.debuff_taken_damage_percent_boost:
            if _match_damage_type(effect.damage_type, damage_type):
                if damage_type == DamageType.physical:
                    pr -= value
                elif damage_type == DamageType.magical:
                    mr -= value
                elif damage_type == DamageType.fixed:
                    fr -= value

    return pr, mr, fr


def get_incoming_flat_damage_modifiers(
    spirit: BattleSpirit,
) -> Tuple[float, float, float]:
    """Deprecated: flat incoming modifiers are no longer used."""
    return 0.0, 0.0, 0.0


def get_damage_caps(spirit: BattleSpirit) -> Dict[DamageType, float]:
    """Return the strictest damage cap by damage type."""
    caps: Dict[DamageType, float] = {}
    for effect in spirit.effects:
        if effect.type != EffectType.buff_damage_cap or effect.value is None:
            continue
        value = effect.value
        if effect.damage_type is None:
            for cap_type in (DamageType.physical, DamageType.magical):
                caps[cap_type] = min(value, caps.get(cap_type, float("inf")))
        else:
            caps[effect.damage_type] = min(
                value,
                caps.get(effect.damage_type, float("inf")),
            )
    return caps


def get_def_pierce(attacker: BattleSpirit, damage_type: DamageType) -> float:
    """Sum of the attacker's ``buff_def_pierce`` effects matching ``damage_type``."""
    total = 0.0
    for effect in attacker.effects:
        if effect.type != EffectType.buff_def_pierce or effect.value is None:
            continue
        if _match_damage_type(effect.damage_type, damage_type):
            total += effect.value
    return total
