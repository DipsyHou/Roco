"""Typed battle action payloads shared by core, AI, and UI."""

from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class ActionDict(TypedDict, total=False):
    type: str
    playerId: str
    actorId: str
    skillId: str
    targetId: str
    discardHandIndices: List[int]
    cardHandIndex: int
    newCardId: str
    consumeHandIndex: int
    consumeHandIndices: List[int]
    previewDish: bool
    # Preserve forward compatibility for any extra client-only fields.
    extra: Dict[str, Any]

