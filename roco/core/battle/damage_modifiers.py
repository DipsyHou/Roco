"""Damage modifier extraction helpers."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from .stats import get_effective_stat
from .types import BattleSpirit, DamageType, EffectType, StatType

DEFAULT_CRIT_DAMAGE_PERCENT = 100.0


def _match_damage_type(
    eff_dt: Optional[DamageType],
    target_dt: DamageType,
) -> bool:
    """``None`` means the modifier applies to every damage type."""
    return eff_dt is None or eff_dt == target_dt


def get_damage_modifiers(
    spirit: BattleSpirit,
) -> Tuple[float, float, float, float, float, float]:
    """Attacker percent inc/dec by damage type."""
    pi = mi = fi = pd = md = fd = 0.0

    for effect in spirit.effects:
        if effect.value is None:
            continue
        value = effect.value
        if effect.type == EffectType.buff_damage_percent_boost:
            if _match_damage_type(effect.damage_type, DamageType.physical):
                pi += value
            if _match_damage_type(effect.damage_type, DamageType.magical):
                mi += value
            if _match_damage_type(effect.damage_type, DamageType.fixed):
                fi += value
        elif effect.type == EffectType.debuff_damage_percent_reduction:
            if _match_damage_type(effect.damage_type, DamageType.physical):
                pd += value
            if _match_damage_type(effect.damage_type, DamageType.magical):
                md += value
            if _match_damage_type(effect.damage_type, DamageType.fixed):
                fd += value

    return pi, mi, fi, pd, md, fd


def get_flat_damage_modifiers(
    spirit: BattleSpirit,
) -> Tuple[float, float, float, float, float, float]:
    """Attacker flat inc/dec by damage type."""
    pi = mi = fi = pd = md = fd = 0.0

    for effect in spirit.effects:
        if effect.value is None:
            continue
        value = effect.value
        if effect.type == EffectType.buff_damage_flat_boost:
            if _match_damage_type(effect.damage_type, DamageType.physical):
                pi += value
            if _match_damage_type(effect.damage_type, DamageType.magical):
                mi += value
            if _match_damage_type(effect.damage_type, DamageType.fixed):
                fi += value
        elif effect.type == EffectType.debuff_damage_flat_reduction:
            if _match_damage_type(effect.damage_type, DamageType.physical):
                pd += value
            if _match_damage_type(effect.damage_type, DamageType.magical):
                md += value
            if _match_damage_type(effect.damage_type, DamageType.fixed):
                fd += value

    return pi, mi, fi, pd, md, fd


def get_incoming_damage_modifiers(spirit: BattleSpirit) -> Tuple[float, float, float]:
    """Defender percent reductions by damage type; negative values increase damage."""
    pr = mr = fr = 0.0

    for effect in spirit.effects:
        if effect.value is None:
            continue
        value = effect.value
        if effect.type == EffectType.buff_taken_damage_percent_reduction:
            if _match_damage_type(effect.damage_type, DamageType.physical):
                pr += value
            if _match_damage_type(effect.damage_type, DamageType.magical):
                mr += value
            if _match_damage_type(effect.damage_type, DamageType.fixed):
                fr += value
        elif effect.type == EffectType.debuff_taken_damage_percent_boost:
            if effect.effect_tag == "sustained_damage":
                continue
            if _match_damage_type(effect.damage_type, DamageType.physical):
                pr -= value
            if _match_damage_type(effect.damage_type, DamageType.magical):
                mr -= value
            if _match_damage_type(effect.damage_type, DamageType.fixed):
                fr -= value

    return pr, mr, fr


def get_incoming_flat_damage_modifiers(
    spirit: BattleSpirit,
) -> Tuple[float, float, float]:
    """Defender flat reductions by damage type; negative values increase damage."""
    pr = mr = fr = 0.0

    for effect in spirit.effects:
        if effect.value is None:
            continue
        value = effect.value
        if effect.type == EffectType.buff_taken_damage_flat_reduction:
            if _match_damage_type(effect.damage_type, DamageType.physical):
                pr += value
            if _match_damage_type(effect.damage_type, DamageType.magical):
                mr += value
            if _match_damage_type(effect.damage_type, DamageType.fixed):
                fr += value
        elif effect.type == EffectType.debuff_taken_damage_flat_boost:
            if _match_damage_type(effect.damage_type, DamageType.physical):
                pr -= value
            if _match_damage_type(effect.damage_type, DamageType.magical):
                mr -= value
            if _match_damage_type(effect.damage_type, DamageType.fixed):
                fr -= value

    return pr, mr, fr


def get_damage_caps(spirit: BattleSpirit) -> Dict[DamageType, float]:
    """Return the strictest damage cap by damage type."""
    caps: Dict[DamageType, float] = {}
    for effect in spirit.effects:
        if effect.type != EffectType.buff_damage_cap or effect.value is None:
            continue
        value = effect.value
        if effect.damage_type is None:
            for damage_type in (DamageType.physical, DamageType.magical, DamageType.fixed):
                caps[damage_type] = min(value, caps.get(damage_type, float("inf")))
        else:
            caps[effect.damage_type] = min(
                value,
                caps.get(effect.damage_type, float("inf")),
            )
    return caps


def get_crit_stats(
    attacker: BattleSpirit, target: Optional[BattleSpirit] = None
) -> Tuple[float, float]:
    """Return (crit_rate capped 0~1, crit_damage_percent). Base crit damage is 100%."""
    from ..spirits import get_spirit_logic

    crit_rate = 0.0
    crit_damage_percent = DEFAULT_CRIT_DAMAGE_PERCENT

    for effect in attacker.effects:
        if effect.value is None:
            continue
        if effect.type == EffectType.buff_crit_rate:
            crit_rate += effect.value
        elif effect.type == EffectType.buff_crit_damage:
            crit_damage_percent += effect.value

    logic = get_spirit_logic(attacker.template_id)
    if logic:
        crit_rate += logic.get_crit_rate_bonus(attacker, target)
        crit_damage_percent += logic.get_crit_damage_bonus(attacker, target)

    crit_rate = min(1.0, max(0.0, crit_rate))
    crit_damage_percent = max(0.0, crit_damage_percent)
    return crit_rate, crit_damage_percent


def get_def_pierce(attacker: BattleSpirit, damage_type: DamageType) -> float:
    """Sum of the attacker's ``buff_def_pierce`` effects matching ``damage_type``."""
    total = 0.0
    for effect in attacker.effects:
        if effect.type != EffectType.buff_def_pierce or effect.value is None:
            continue
        if _match_damage_type(effect.damage_type, damage_type):
            total += effect.value
    return total


def _apply_crit_to_base(
    base: float,
    attacker: BattleSpirit,
    *,
    target: Optional[BattleSpirit] = None,
    crit_flag: Optional[list[bool]] = None,
    rng: Optional[object] = None,
) -> Tuple[float, bool]:
    """Return (result, was_crit). All damage checks crit; 0% rate skips RNG."""
    import random as _random

    if base <= 0:
        return base, False
    crit_rate, crit_damage_percent = get_crit_stats(attacker, target)
    if crit_rate <= 0:
        return base, False
    roll = rng.random() if rng is not None else _random.random()
    if roll < crit_rate:
        if crit_flag is not None:
            crit_flag.append(True)
        return base * (crit_damage_percent / 100.0), True
    return base, False
