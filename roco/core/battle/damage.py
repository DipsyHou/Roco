"""Damage formula and compatibility exports."""

from __future__ import annotations

import random
from typing import List, Literal, Optional

from .crit import DEFAULT_CRIT_DAMAGE_PERCENT, apply_crit_to_base, get_crit_stats
from .damage_modifiers import (
    DamageModifierMode,
    get_damage_caps,
    get_damage_modifiers,
    get_def_pierce,
    get_flat_damage_modifiers,
    get_incoming_damage_modifiers,
    get_incoming_flat_damage_modifiers,
)
from .stats import _STAT_ENGINE_ATTR, get_effective_stat
from .types import BattleSpirit, DamageType, StatType

SustainedKind = Optional[Literal["burn", "poison"]]


def _modifier_mode(sustained: SustainedKind) -> DamageModifierMode:
    if sustained == "burn":
        return DamageModifierMode.sustained_burn
    if sustained == "poison":
        return DamageModifierMode.sustained_poison
    return DamageModifierMode.normal


def _sum_ally_aura(spirit: BattleSpirit, hook_name: str) -> float:
    """聚合同队存活精灵为 ``spirit`` 提供的某个伤害光环钩子（通用、与精灵无关）。"""
    engine = getattr(spirit, _STAT_ENGINE_ATTR, None)
    if engine is None:
        return 0.0
    from ..spirits import get_spirit_logic

    total = 0.0
    for source in engine.get_all_spirits(spirit.owner_id):
        if not source.is_alive:
            continue
        logic = get_spirit_logic(source.template_id)
        if logic is not None:
            total += getattr(logic, hook_name)(engine, source, spirit)
    return total


def _calculate_fixed_damage(
    raw_damage: float,
    attacker: Optional[BattleSpirit],
    defender: BattleSpirit,
    *,
    mode: DamageModifierMode,
) -> int:
    """Fixed damage: no crit; only explicit fixed-% effects and 硬化肌肤-style hooks."""
    from ..spirits import get_spirit_logic

    result = raw_damage

    if attacker is not None:
        _, _, fi, _, _, fd = get_damage_modifiers(attacker, DamageType.fixed, mode)
        result *= 1 + (fi - fd)

    _, _, def_fr = get_incoming_damage_modifiers(defender, DamageType.fixed, mode)
    dec_pct = def_fr

    logic = get_spirit_logic(defender.template_id)
    if logic:
        dec_pct += logic.get_incoming_damage_reduction(defender, DamageType.fixed)

    dec_pct = min(dec_pct, 0.8)
    result *= 1 - dec_pct

    caps = get_damage_caps(defender)
    if DamageType.fixed in caps:
        result = min(result, caps[DamageType.fixed])

    return max(0, int(result + 1e-9))


def calculate_damage(
    raw_damage: float,
    damage_type: DamageType,
    attacker: Optional[BattleSpirit],
    defender: BattleSpirit,
    *,
    sustained: SustainedKind = None,
    crit_flag: Optional[List[bool]] = None,
    rng: Optional[random.Random] = None,
) -> int:
    """Apply the shared damage pipeline and return final integer damage."""
    from ..spirits import get_spirit_logic

    mode = _modifier_mode(sustained)
    is_sustained = sustained is not None

    if damage_type == DamageType.fixed:
        if sustained == "poison":
            return max(0, int(raw_damage + 1e-9))
        return _calculate_fixed_damage(
            raw_damage, attacker, defender, mode=mode
        )

    pierce = get_def_pierce(attacker, damage_type) if attacker else 0.0
    def_val = (
        get_effective_stat(defender, StatType.def_, extra_percent_bonus=-pierce)
        if damage_type == DamageType.physical
        else get_effective_stat(defender, StatType.mag_def, extra_percent_bonus=-pierce)
    )
    base = (raw_damage * 100 / def_val) if def_val > 0 else raw_damage * 100

    if is_sustained or attacker is None:
        result = base
    else:
        result, _was_crit = apply_crit_to_base(
            base, attacker, target=defender, crit_flag=crit_flag, rng=(rng or random)
        )

    if attacker is not None:
        att_pi, att_mi, att_fi, att_pd, att_md, att_fd = get_damage_modifiers(
            attacker, damage_type, mode
        )
        net_inc = {
            DamageType.physical: att_pi - att_pd,
            DamageType.magical: att_mi - att_md,
        }[damage_type]
        if not is_sustained:
            net_inc += _sum_ally_aura(attacker, "get_aura_damage_percent_bonus")
        result *= 1 + net_inc

    def_pr, def_mr, _ = get_incoming_damage_modifiers(defender, damage_type, mode)
    dec_pct = {
        DamageType.physical: def_pr,
        DamageType.magical: def_mr,
    }[damage_type]

    logic = get_spirit_logic(defender.template_id)
    if logic and not is_sustained:
        dec_pct += logic.get_damage_reduction(defender)

    if not is_sustained:
        dec_pct += _sum_ally_aura(defender, "get_aura_taken_damage_reduction")

    dec_pct = min(dec_pct, 0.8)
    result *= 1 - dec_pct

    if logic:
        result = logic.apply_passive_flat_mitigation(defender, result)

    if not is_sustained:
        caps = get_damage_caps(defender)
        if damage_type in caps:
            result = min(result, caps[damage_type])

    return max(0, int(result + 1e-9))
