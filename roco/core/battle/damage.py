"""Damage formula and compatibility exports."""

from __future__ import annotations

import random
from typing import List, Optional

from .crit import DEFAULT_CRIT_DAMAGE_PERCENT, apply_crit_to_base, get_crit_stats
from .damage_modifiers import (
    _match_damage_type,
    get_damage_caps,
    get_damage_modifiers,
    get_def_pierce,
    get_flat_damage_modifiers,
    get_incoming_damage_modifiers,
    get_incoming_flat_damage_modifiers,
)
from .stats import _STAT_ENGINE_ATTR, get_effective_stat
from .types import BattleSpirit, DamageType, StatType


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

    result, _was_crit = apply_crit_to_base(
        base, attacker, target=defender, crit_flag=crit_flag, rng=(rng or random)
    )

    att_pi, att_mi, att_fi, att_pd, att_md, att_fd = get_damage_modifiers(attacker)
    net_inc = {
        DamageType.physical: att_pi - att_pd,
        DamageType.magical: att_mi - att_md,
        DamageType.fixed: att_fi - att_fd,
    }[damage_type]
    # 同队光环提供的「造成伤害提高」（作用于所有伤害类型，与其他增伤加性叠加）。
    net_inc += _sum_ally_aura(attacker, "get_aura_damage_percent_bonus")
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
        dec_pct += logic.get_incoming_damage_reduction(defender, damage_type)

    # 同队光环提供的「受到伤害降低」。
    dec_pct += _sum_ally_aura(defender, "get_aura_taken_damage_reduction")

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
