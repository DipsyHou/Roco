"""Damage modifier extraction for attribute and fixed damage."""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional, Tuple

from .types import BattleSpirit, DamageType, EffectType

SUSTAINED_DAMAGE_TAG = "sustained_damage"


class DamageModifierMode(str, Enum):
    normal = "normal"
    sustained_burn = "sustained_burn"
    sustained_poison = "sustained_poison"
    sustained_parasite = "sustained_parasite"
    sustained_tianhuo = "sustained_tianhuo"


def _matches(effect_type: Optional[DamageType], damage_type: DamageType) -> bool:
    if effect_type is None:
        return damage_type.is_attribute
    return effect_type == damage_type


def _modifier_applies(effect, damage_type: DamageType, mode: DamageModifierMode) -> bool:
    tagged = effect.effect_tag == SUSTAINED_DAMAGE_TAG
    if tagged:
        return mode != DamageModifierMode.normal and damage_type.is_attribute
    return _matches(effect.damage_type, damage_type)


def get_damage_modifiers(
    spirit: BattleSpirit,
    damage_type: DamageType,
    mode: DamageModifierMode = DamageModifierMode.normal,
) -> Tuple[float, float]:
    """Return outgoing percent increase and reduction."""
    increase = reduction = 0.0
    for effect in spirit.effects:
        if effect.value is None or not _modifier_applies(effect, damage_type, mode):
            continue
        if effect.type == EffectType.buff_damage_percent_boost:
            increase += effect.value
        elif effect.type == EffectType.debuff_damage_percent_reduction:
            reduction += effect.value
    return increase, reduction


def get_incoming_damage_modifiers(
    spirit: BattleSpirit,
    damage_type: DamageType,
    mode: DamageModifierMode = DamageModifierMode.normal,
) -> float:
    """Return incoming percent reduction; negative values are vulnerability."""
    reduction = 0.0
    for effect in spirit.effects:
        if effect.type == EffectType.debuff_fanji and damage_type.is_attribute:
            reduction -= 0.10
            if mode != DamageModifierMode.normal:
                reduction -= 0.20
            continue
        if effect.value is None or not _modifier_applies(effect, damage_type, mode):
            continue
        if effect.type == EffectType.buff_taken_damage_percent_reduction:
            reduction += effect.value
        elif effect.type == EffectType.debuff_taken_damage_percent_boost:
            reduction -= effect.value
    return reduction


def get_damage_caps(spirit: BattleSpirit) -> Dict[Optional[DamageType], float]:
    """Return the strictest cap for each explicit or generic damage scope."""
    caps: Dict[Optional[DamageType], float] = {}
    for effect in spirit.effects:
        if effect.type != EffectType.buff_damage_cap or effect.value is None:
            continue
        key = effect.damage_type
        caps[key] = min(effect.value, caps.get(key, float("inf")))
    return caps


def get_damage_cap(spirit: BattleSpirit, damage_type: DamageType) -> Optional[float]:
    caps = get_damage_caps(spirit)
    candidates = []
    if damage_type in caps:
        candidates.append(caps[damage_type])
    if damage_type.is_attribute and None in caps:
        candidates.append(caps[None])
    return min(candidates) if candidates else None


def get_def_pierce(attacker: BattleSpirit, damage_type: DamageType) -> float:
    if not damage_type.is_attribute:
        return 0.0
    return sum(
        effect.value or 0.0
        for effect in attacker.effects
        if effect.type == EffectType.buff_def_pierce
        and _matches(effect.damage_type, damage_type)
    )
