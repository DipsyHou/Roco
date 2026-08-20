"""巴哈姆特 effect stack helpers."""

from __future__ import annotations

from ..battle.effect_meta import stack_count
from ..battle.types import BattleSpirit, EffectType
from ..battle.utils import make_effect


def has_effect(spirit: BattleSpirit, eff_type: EffectType) -> bool:
    return any(e.type == eff_type for e in spirit.effects)


def get_stacks(spirit: BattleSpirit, eff_type: EffectType) -> int:
    eff = next((e for e in spirit.effects if e.type == eff_type), None)
    return stack_count(eff) if eff else 0


def add_stacks(
    spirit: BattleSpirit,
    eff_type: EffectType,
    amount: int,
    cap: int,
    source_id: str = "",
) -> None:
    if amount <= 0:
        return
    eff = next((e for e in spirit.effects if e.type == eff_type), None)
    if eff:
        eff.stacks = min(cap, stack_count(eff) + amount)
    else:
        spirit.effects.append(
            make_effect(eff_type, source_id or spirit.unique_id, stacks=min(cap, amount))
        )


def remove_stacks(spirit: BattleSpirit, eff_type: EffectType, amount: int) -> int:
    """Remove stacks and return actual amount removed; delete effect if zero."""
    eff = next((e for e in spirit.effects if e.type == eff_type), None)
    if not eff:
        return 0
    removed = min(stack_count(eff), amount)
    eff.stacks = stack_count(eff) - removed
    if stack_count(eff) <= 0:
        spirit.effects = [e for e in spirit.effects if e.type != eff_type]
    return removed


def remove_effect(spirit: BattleSpirit, eff_type: EffectType) -> None:
    spirit.effects = [e for e in spirit.effects if e.type != eff_type]
