"""Deck / hand state for card-based spirits (no battle dependencies)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from ..battle.rng import seeded_random

TURN_START_DRAW = 3

TAROT_CARDS: tuple[str, ...] = (
    "sun",
    "moon",
    "star",
    "temperance",
    "judgment",
    "tower",
    "chariot",
    "hermit",
    "death",
    "fool",
    "demon",
)

# Back-compat alias
FATE_CARDS = TAROT_CARDS

CARD_LABELS: Dict[str, str] = {
    "sun": "\u592a\u9633",
    "moon": "\u6708\u4eae",
    "star": "\u661f\u661f",
    "temperance": "\u8282\u5236",
    "judgment": "\u5ba1\u5224",
    "tower": "\u9ad8\u5854",
    "chariot": "\u6218\u8f66",
    "hermit": "\u9690\u58eb",
    "death": "\u6b7b\u795e",
    "fool": "\u611a\u8005",
    "demon": "\u6076\u9b54",
}

ALLY_TARGET_CARDS = frozenset({"star", "tower", "chariot", "hermit"})
ENEMY_TARGET_CARDS = frozenset({"temperance", "judgment"})


def card_label(card_id: str) -> str:
    return CARD_LABELS.get(card_id, card_id)


CARD_SKILLS: frozenset[str] = frozenset(
    {"guifashi_draw", "guifashi_show", "guifashi_cheat"}
)


@dataclass
class CardState:
    deck: List[str] = field(default_factory=list)
    hand: List[str] = field(default_factory=list)
    consumed: List[str] = field(default_factory=list)
    draw_count: int = 0
    return_count: int = 0
    pending_moon_energy: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deck": list(self.deck),
            "hand": list(self.hand),
            "consumed": list(self.consumed),
            "drawCount": self.draw_count,
            "returnCount": self.return_count,
            "pendingMoonEnergy": self.pending_moon_energy,
        }

    @classmethod
    def from_dict(cls, raw: Optional[Dict[str, Any]]) -> "CardState":
        if not raw:
            return cls()
        return cls(
            deck=list(raw.get("deck") or []),
            hand=list(raw.get("hand") or []),
            consumed=list(raw.get("consumed") or []),
            draw_count=int(raw.get("drawCount", raw.get("draw_count", 0)) or 0),
            return_count=int(raw.get("returnCount", raw.get("return_count", 0)) or 0),
            pending_moon_energy=bool(
                raw.get("pendingMoonEnergy", raw.get("pending_moon_energy", False))
            ),
        )


def build_fate_deck(battle_id: str, spirit_id: str) -> List[str]:
    deck = list(TAROT_CARDS)
    rng = seeded_random(battle_id, spirit_id, "init")
    rng.shuffle(deck)
    return deck


def draw_card(state: CardState, battle_id: str, spirit_id: str) -> Optional[str]:
    if not state.deck:
        return None
    rng = seeded_random(battle_id, spirit_id, "draw", state.draw_count)
    state.draw_count += 1
    card = state.deck.pop(rng.randrange(len(state.deck)))
    state.hand.append(card)
    return card


def draw_cards(
    state: CardState,
    battle_id: str,
    spirit_id: str,
    count: int,
) -> int:
    drawn = 0
    for _ in range(count):
        if draw_card(state, battle_id, spirit_id) is None:
            break
        drawn += 1
    return drawn


def return_card_to_deck(
    state: CardState,
    card: str,
    battle_id: str,
    spirit_id: str,
) -> None:
    rng = seeded_random(battle_id, spirit_id, "return", state.return_count)
    state.return_count += 1
    insert_at = rng.randrange(len(state.deck) + 1)
    state.deck.insert(insert_at, card)


def remove_hand_card(state: CardState, index: int) -> str:
    return state.hand.pop(index)


def consume_hand_card(state: CardState, index: int) -> str:
    card = state.hand.pop(index)
    state.consumed.append(card)
    return card


def adjust_consume_indices_after_show(
    indices: Sequence[int],
    shown_index: int,
) -> List[int]:
    """``indices`` are relative to the hand before the shown card is removed."""
    out: List[int] = []
    for i in indices:
        idx = int(i)
        if idx == shown_index:
            continue
        out.append(idx - 1 if idx > shown_index else idx)
    return out


def consume_hand_cards(state: CardState, indices: Sequence[int]) -> List[str]:
    """Remove hand cards at ``indices`` into the consumed pile (high index first)."""
    unique = sorted({int(i) for i in indices}, reverse=True)
    removed: List[str] = []
    for idx in unique:
        if idx < 0 or idx >= len(state.hand):
            raise ValueError(f"invalid hand index: {idx}")
        removed.append(consume_hand_card(state, idx))
    removed.reverse()
    return removed


def transform_hand_card(state: CardState, index: int, new_card: str) -> str:
    old = state.hand[index]
    state.hand[index] = new_card
    return old


def discard_all_hand(
    state: CardState,
    battle_id: str,
    spirit_id: str,
) -> List[str]:
    """Turn end: return every hand card to the deck."""
    discarded: List[str] = []
    while state.hand:
        card = state.hand.pop(0)
        return_card_to_deck(state, card, battle_id, spirit_id)
        discarded.append(card)
    return discarded
