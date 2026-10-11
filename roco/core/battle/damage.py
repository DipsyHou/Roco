"""Shared attribute and fixed damage calculation."""

from __future__ import annotations

import random
from typing import List, Literal, Optional

from .crit import apply_crit_to_base, get_crit_stats
from .damage_modifiers import (
    DamageModifierMode,
    get_damage_cap,
    get_damage_caps,
    get_damage_modifiers,
    get_def_pierce,
    get_incoming_damage_modifiers,
)
from .resistance import resistance_for
from .stats import _STAT_ENGINE_ATTR, get_effective_stat
from .types import BattleSpirit, DamageType, StatType

SustainedKind = Optional[Literal["burn", "poison", "parasite", "tianhuo"]]


def _modifier_mode(sustained: SustainedKind) -> DamageModifierMode:
    return {
        "burn": DamageModifierMode.sustained_burn,
        "poison": DamageModifierMode.sustained_poison,
        "parasite": DamageModifierMode.sustained_parasite,
        "tianhuo": DamageModifierMode.sustained_tianhuo,
    }.get(sustained, DamageModifierMode.normal)


def _sum_ally_aura(spirit: BattleSpirit, hook_name: str) -> float:
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


def _notify_ally_damage_recorded(
    attacker: Optional[BattleSpirit],
    defender: BattleSpirit,
    amount: float,
    *,
    sustained: SustainedKind = None,
) -> None:
    if attacker is None or amount <= 0:
        return
    recorded = max(0, int(amount + 1e-9))
    if recorded <= 0:
        return
    engine = getattr(attacker, _STAT_ENGINE_ATTR, None) or getattr(
        defender, _STAT_ENGINE_ATTR, None
    )
    if engine is None:
        return
    from ..spirits import get_spirit_logic

    for spirit in engine.get_all_spirits(attacker.owner_id):
        if not spirit.is_alive:
            continue
        logic = get_spirit_logic(spirit.template_id)
        if logic is not None:
            logic.on_ally_damage_recorded(
                engine, spirit, attacker, defender, recorded
            )


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
    """Apply the common damage pipeline and return final integer damage."""
    from ..spirits import get_spirit_logic

    mode = _modifier_mode(sustained)
    logic = get_spirit_logic(defender.template_id)
    result = raw_damage

    if damage_type.is_attribute:
        pierce = get_def_pierce(attacker, damage_type) if attacker else 0.0
        defense = get_effective_stat(
            defender, StatType.defense, extra_percent_bonus=-pierce
        )
        result *= 200.0 / (100.0 + max(0.0, defense))

        if sustained is None and attacker is not None:
            result, _ = apply_crit_to_base(
                result,
                attacker,
                target=defender,
                crit_flag=crit_flag,
                rng=(rng or random),
            )

        if attacker is not None:
            increase, reduction = get_damage_modifiers(attacker, damage_type, mode)
            result *= 1 + increase - reduction + _sum_ally_aura(
                attacker, "get_aura_damage_percent_bonus"
            )

        incoming_reduction = get_incoming_damage_modifiers(
            defender, damage_type, mode
        )
        if logic:
            incoming_reduction += logic.get_damage_reduction(defender)
        incoming_reduction += _sum_ally_aura(
            defender, "get_aura_taken_damage_reduction"
        )
        result *= 1 - min(incoming_reduction, 0.8)
        result *= 1 - resistance_for(defender.elements, damage_type)
    else:
        if attacker is not None:
            increase, reduction = get_damage_modifiers(attacker, damage_type, mode)
            result *= 1 + increase - reduction
        incoming_reduction = get_incoming_damage_modifiers(
            defender, damage_type, mode
        )
        if logic:
            incoming_reduction += logic.get_incoming_damage_reduction(
                defender, damage_type
            )
        result *= 1 - min(incoming_reduction, 0.8)

    cap = get_damage_cap(defender, damage_type)
    if cap is not None:
        result = min(result, cap)
    _notify_ally_damage_recorded(attacker, defender, result, sustained=sustained)
    if logic:
        result = logic.apply_passive_flat_mitigation(defender, result)
    return max(0, int(result + 1e-9))


__all__ = [
    "calculate_damage",
    "get_crit_stats",
    "get_damage_caps",
    "get_damage_modifiers",
]
