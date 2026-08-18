"""Damage modifier extraction and damage formula."""

from __future__ import annotations

import random
from typing import Dict, Optional, Tuple, List

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
            # 持续伤害专用增伤（如毛血旺）只在 DoT 管线结算，不进普攻/技能。
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


def _apply_crit_to_base(
    base: float,
    attacker: BattleSpirit,
    *,
    target: Optional[BattleSpirit] = None,
    crit_flag: Optional[List[bool]] = None,
    rng: Optional[random.Random] = None,
) -> Tuple[float, bool]:
    """Return (result, was_crit). All damage uses crit rate / crit damage; rate 0 skips."""
    if base <= 0:
        return base, False
    crit_rate, crit_damage_percent = get_crit_stats(attacker, target)
    if crit_rate <= 0:
        return base, False
    roll = rng.random() if rng is not None else random.random()
    if roll < crit_rate:
        if crit_flag is not None:
            crit_flag.append(True)
        return base * (crit_damage_percent / 100.0), True
    return base, False


def get_def_pierce(attacker: BattleSpirit, damage_type: DamageType) -> float:
    """Sum of the attacker's ``buff_def_pierce`` effects matching ``damage_type``.

    "无视防御"不修改防御方的真实数值：它只在*这一段伤害*的基础值计算中，
    让防御方的有效防御被视为按这个百分点降低（见 ``get_effective_stat`` 的
    ``extra_percent_bonus``）。多个来源的穿透按百分点相加，与其它百分比
    修饰符共用同一套加算规则，不会像倍率相乘那样失控。
    """
    total = 0.0
    for effect in attacker.effects:
        if effect.type != EffectType.buff_def_pierce or effect.value is None:
            continue
        if _match_damage_type(effect.damage_type, damage_type):
            total += effect.value
    return total


def calculate_damage(
    raw_damage: float,
    damage_type: DamageType,
    attacker: BattleSpirit,
    defender: BattleSpirit,
    *,
    crit_flag: Optional[List[bool]] = None,
    rng: Optional[random.Random] = None,
) -> int:
    """Apply the shared damage pipeline and return final integer damage."""
    from ..spirits import get_spirit_logic

    if damage_type == DamageType.fixed:
        base = raw_damage
    else:
        pierce = get_def_pierce(attacker, damage_type)
        def_val = (
            get_effective_stat(defender, StatType.def_, extra_percent_bonus=-pierce)
            if damage_type == DamageType.physical
            else get_effective_stat(defender, StatType.mag_def, extra_percent_bonus=-pierce)
        )
        base = (raw_damage * 100 / def_val) if def_val > 0 else raw_damage * 100

    result, _was_crit = _apply_crit_to_base(
        base, attacker, target=defender, crit_flag=crit_flag, rng=rng
    )

    att_pi, att_mi, att_fi, att_pd, att_md, att_fd = get_damage_modifiers(attacker)
    net_inc = {
        DamageType.physical: att_pi - att_pd,
        DamageType.magical: att_mi - att_md,
        DamageType.fixed: att_fi - att_fd,
    }[damage_type]
    result *= 1 + net_inc

    fpi, fmi, ffi, fpd, fmd, ffd = get_flat_damage_modifiers(attacker)
    flat_inc = {
        DamageType.physical: fpi - fpd,
        DamageType.magical: fmi - fmd,
        DamageType.fixed: ffi - ffd,
    }[damage_type]
    result += flat_inc

    def_pr, def_mr, def_fr = get_incoming_damage_modifiers(defender)
    dec_pct = {
        DamageType.physical: def_pr,
        DamageType.magical: def_mr,
        DamageType.fixed: def_fr,
    }[damage_type]

    logic = get_spirit_logic(defender.template_id)
    if logic:
        dec_pct += logic.get_damage_reduction(defender)

    dec_pct = min(dec_pct, 0.8)
    result *= 1 - dec_pct

    def_fpr, def_fmr, def_ffr = get_incoming_flat_damage_modifiers(defender)
    flat_dec = {
        DamageType.physical: def_fpr,
        DamageType.magical: def_fmr,
        DamageType.fixed: def_ffr,
    }[damage_type]
    result -= flat_dec

    if logic:
        result = logic.apply_passive_flat_mitigation(defender, result)

    caps = get_damage_caps(defender)
    if damage_type in caps:
        result = min(result, caps[damage_type])

    return max(0, int(result + 1e-9))
