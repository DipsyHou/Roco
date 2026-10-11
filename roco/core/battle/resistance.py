"""Intrinsic elemental resistance rules."""

from __future__ import annotations

from typing import Iterable, Mapping

from .types import DamageType

# Values are fractions: 0.25 means 25% resistance, -0.25 means a 25%
# weakness. The table is intentionally data-only so it can be audited without
# tracing the damage pipeline.
ELEMENTAL_RESISTANCES: Mapping[DamageType, Mapping[DamageType, float]] = {
    DamageType.fire: {
        DamageType.fire: 0.0, DamageType.water: -0.25, DamageType.grass: 0.25,
        DamageType.ground: -0.25, DamageType.wind: 0.0, DamageType.physical: 0.0,
        DamageType.ice: 0.25, DamageType.electric: 0.0, DamageType.poison: 0.0,
        DamageType.light: 0.0, DamageType.dark: 0.0, DamageType.dragon: 0.0,
    },
    DamageType.water: {
        DamageType.fire: 0.25, DamageType.water: 0.0, DamageType.grass: -0.25,
        DamageType.ground: 0.0, DamageType.wind: 0.0, DamageType.physical: 0.0,
        DamageType.ice: 0.25, DamageType.electric: -0.25, DamageType.poison: 0.0,
        DamageType.light: 0.0, DamageType.dark: 0.0, DamageType.dragon: 0.0,
    },
    DamageType.grass: {
        DamageType.fire: -0.25, DamageType.water: 0.25, DamageType.grass: 0.25,
        DamageType.ground: 0.25, DamageType.wind: -0.25, DamageType.physical: 0.0,
        DamageType.ice: -0.25, DamageType.electric: 0.25, DamageType.poison: -0.25,
        DamageType.light: 0.25, DamageType.dark: -0.25, DamageType.dragon: 0.0,
    },
    DamageType.ground: {
        DamageType.fire: 0.0, DamageType.water: -0.25, DamageType.grass: -0.25,
        DamageType.ground: 0.25, DamageType.wind: 0.0, DamageType.physical: 0.0,
        DamageType.ice: -0.25, DamageType.electric: 0.0, DamageType.poison: 0.25,
        DamageType.light: 0.0, DamageType.dark: 0.0, DamageType.dragon: 0.0,
    },
    DamageType.wind: {
        DamageType.fire: 0.0, DamageType.water: 0.0, DamageType.grass: 0.25,
        DamageType.ground: -0.25, DamageType.wind: 0.0, DamageType.physical: 0.25,
        DamageType.ice: -0.25, DamageType.electric: -0.25, DamageType.poison: 0.0,
        DamageType.light: 0.0, DamageType.dark: 0.0, DamageType.dragon: 0.0,
    },
    DamageType.physical: {
        DamageType.fire: 0.0, DamageType.water: 0.0, DamageType.grass: 0.0,
        DamageType.ground: 0.25, DamageType.wind: -0.25, DamageType.physical: 0.0,
        DamageType.ice: 0.0, DamageType.electric: 0.0, DamageType.poison: -0.25,
        DamageType.light: 0.0, DamageType.dark: 0.25, DamageType.dragon: 0.0,
    },
    DamageType.ice: {
        DamageType.fire: -0.25, DamageType.water: 0.0, DamageType.grass: 0.0,
        DamageType.ground: -0.25, DamageType.wind: 0.0, DamageType.physical: -0.25,
        DamageType.ice: 0.25, DamageType.electric: 0.0, DamageType.poison: 0.0,
        DamageType.light: 0.0, DamageType.dark: 0.0, DamageType.dragon: 0.0,
    },
    DamageType.electric: {
        DamageType.fire: 0.0, DamageType.water: 0.0, DamageType.grass: 0.0,
        DamageType.ground: -0.25, DamageType.wind: 0.25, DamageType.physical: 0.0,
        DamageType.ice: 0.0, DamageType.electric: 0.25, DamageType.poison: 0.0,
        DamageType.light: 0.0, DamageType.dark: 0.0, DamageType.dragon: 0.0,
    },
    DamageType.poison: {
        DamageType.fire: 0.0, DamageType.water: 0.0, DamageType.grass: 0.25,
        DamageType.ground: -0.25, DamageType.wind: 0.0, DamageType.physical: 0.25,
        DamageType.ice: 0.0, DamageType.electric: 0.0, DamageType.poison: 0.25,
        DamageType.light: 0.0, DamageType.dark: 0.0, DamageType.dragon: 0.0,
    },
    DamageType.light: {
        DamageType.fire: 0.0, DamageType.water: 0.0, DamageType.grass: 0.0,
        DamageType.ground: 0.0, DamageType.wind: 0.0, DamageType.physical: 0.0,
        DamageType.ice: 0.0, DamageType.electric: 0.0, DamageType.poison: 0.0,
        DamageType.light: 0.25, DamageType.dark: -0.25, DamageType.dragon: 0.0,
    },
    DamageType.dark: {
        DamageType.fire: 0.0, DamageType.water: 0.0, DamageType.grass: 0.0,
        DamageType.ground: 0.0, DamageType.wind: 0.0, DamageType.physical: 0.0,
        DamageType.ice: 0.0, DamageType.electric: 0.0, DamageType.poison: 0.0,
        DamageType.light: -0.25, DamageType.dark: 0.25, DamageType.dragon: 0.0,
    },
    DamageType.dragon: {
        DamageType.fire: 0.25, DamageType.water: 0.25, DamageType.grass: 0.25,
        DamageType.ground: 0.0, DamageType.wind: 0.0, DamageType.physical: 0.0,
        DamageType.ice: -0.25, DamageType.electric: 0.25, DamageType.poison: 0.0,
        DamageType.light: 0.0, DamageType.dark: 0.0, DamageType.dragon: -0.25,
    },
}


def resistance_for(elements: Iterable[DamageType], damage_type: DamageType) -> float:
    """Return summed intrinsic resistance.

    Negative resistance deliberately has no lower bound. Positive resistance
    is capped at 100% so the resulting damage multiplier cannot become
    negative.
    """
    if not damage_type.is_attribute:
        return 0.0
    total = sum(
        ELEMENTAL_RESISTANCES.get(element, {}).get(damage_type, 0.0)
        for element in elements
        if element.is_attribute
    )
    return min(1.0, total)
