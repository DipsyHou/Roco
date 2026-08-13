"""Timeline scheduler — action value = charge / speed, global time advance."""

from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple, TypeVar

ACTION_GAP = 10000
TIMELINE_PREVIEW_COUNT = 20

T = TypeVar("T")


def action_value(charge: float, speed: float) -> float:
    if speed <= 0:
        return float("inf")
    return charge / speed


def adjust_charge_advance(charge: float, percent: float) -> float:
    """行动提前：路程 = max(0, 路程 - ACTION_GAP * 比例)；行动值 = 路程 / 速度。"""
    return max(0.0, charge - ACTION_GAP * percent)


def adjust_charge_delay(charge: float, percent: float) -> float:
    """行动延后：路程 = 路程 + ACTION_GAP * 比例；行动值 = 路程 / 速度。"""
    return max(0.0, charge + ACTION_GAP * percent)


def pick_next_actor(
    entries: Sequence[Tuple[T, float, int, str]],
) -> Optional[T]:
    """Pick entry with min action_value; tie-break higher speed, then unique_id."""
    if not entries:
        return None
    best = min(entries, key=lambda e: (action_value(e[1], e[2]), -e[2], e[3]))
    return best[0]


def advance_time(
    charges: List[float],
    speeds: List[float],
    v: float,
) -> None:
    """Advance global time by V: each charge -= V * speed."""
    for i in range(len(charges)):
        charges[i] -= v * speeds[i]


def compute_timeline_preview(
    spirits: Sequence[T],
    charge_fn: Callable[[T], float],
    speed_fn: Callable[[T], float],
    id_fn: Callable[[T], str],
    count: int = 5,
) -> List[T]:
    """Simulate next `count` actors without mutating state."""
    if not spirits:
        return []
    charges = [charge_fn(s) for s in spirits]
    speeds = [max(1, speed_fn(s)) for s in spirits]
    ids = [id_fn(s) for s in spirits]
    preview: List[T] = []
    working = list(spirits)

    for _ in range(count):
        entries = [
            (working[i], charges[i], speeds[i], ids[i])
            for i in range(len(working))
        ]
        actor = pick_next_actor(entries)
        if actor is None:
            break
        idx = working.index(actor)
        v = action_value(charges[idx], speeds[idx])
        advance_time(charges, speeds, v)
        charges[idx] += ACTION_GAP
        preview.append(actor)

    return preview
