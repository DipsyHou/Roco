"""藤椒小巴 state keys and 火力 helpers."""

from __future__ import annotations

from typing import List, Optional

from ..battle.types import BattleSpirit, EffectType
from ..battle.utils import make_effect

PENDING_FREE_KEY = "pending_free"
COMMITTED_DISH_KEY = "committed_dish"

DISH_LAZIJI = "laziji"
DISH_SHUIZHUYU = "shuizhuyu"
DISH_MAOXUEWANG = "maoxuewang"

HUOLI_THRESHOLDS: tuple[tuple[int, str], ...] = (
    (10, DISH_LAZIJI),
    (20, DISH_SHUIZHUYU),
    (30, DISH_MAOXUEWANG),
)


def pending_free(spirit: BattleSpirit) -> List[str]:
    raw = spirit.sync_attrs.get(PENDING_FREE_KEY)
    return list(raw) if raw else []


def set_pending_free(spirit: BattleSpirit, pending: List[str]) -> None:
    if pending:
        spirit.sync_attrs[PENDING_FREE_KEY] = list(pending)
    else:
        spirit.sync_attrs.pop(PENDING_FREE_KEY, None)


def committed_dish(spirit: BattleSpirit) -> Optional[str]:
    raw = spirit.sync_attrs.get(COMMITTED_DISH_KEY)
    return str(raw) if raw else None


def set_committed_dish(spirit: BattleSpirit, dish: Optional[str]) -> None:
    if dish:
        spirit.sync_attrs[COMMITTED_DISH_KEY] = dish
    else:
        spirit.sync_attrs.pop(COMMITTED_DISH_KEY, None)


def huoli_stacks(spirit: BattleSpirit) -> int:
    eff = next((e for e in spirit.effects if e.type == EffectType.state_huoli), None)
    return max(0, eff.stacks) if eff else 0


def set_huoli(spirit: BattleSpirit, stacks: int) -> None:
    stacks = max(0, stacks)
    eff = next((e for e in spirit.effects if e.type == EffectType.state_huoli), None)
    if stacks <= 0:
        if eff:
            spirit.effects = [e for e in spirit.effects if e.type != EffectType.state_huoli]
        return
    if eff:
        eff.stacks = stacks
    else:
        spirit.effects.append(
            make_effect(EffectType.state_huoli, spirit.unique_id, stacks=stacks)
        )


def consume_all_huoli(spirit: BattleSpirit) -> int:
    amount = huoli_stacks(spirit)
    set_huoli(spirit, 0)
    return amount
