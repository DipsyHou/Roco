"""Formation helpers: slot adjacency among living spirits."""

from __future__ import annotations

from typing import List, Sequence, TypeVar

from .types import BattleSpirit

T = TypeVar("T", bound=BattleSpirit)


def living_slot_neighbors(spirits: Sequence[T], target: T) -> List[T]:
    """Left/right neighbors by slot among living units; dead slots do not block."""
    ordered = sorted((s for s in spirits if s.is_alive), key=lambda s: s.slot)
    for i, spirit in enumerate(ordered):
        if spirit.unique_id != target.unique_id:
            continue
        out: List[T] = []
        if i > 0:
            out.append(ordered[i - 1])
        if i + 1 < len(ordered):
            out.append(ordered[i + 1])
        return out
    return []
