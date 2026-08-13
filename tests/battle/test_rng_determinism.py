"""Characterization guardrails for deterministic RNG and full-battle serialization.

These tests lock in behavior we must preserve across the structural refactor:
- Seeded card decks reproduce for the same (battle_id, spirit_id).
- A scripted battle serializes and round-trips into a stable snapshot.
"""

from __future__ import annotations

from copy import deepcopy

from tests.conftest import P1, P2, skip_active

from roco.core.battle.rng import RandomSource, seeded_random
from roco.core.battle.types import BattlePhase
from roco.core.spirits.guifashi_cards import (
    CardState,
    build_fate_deck,
    draw_card,
    return_card_to_deck,
)
from roco.net.serialize import state_from_dict, state_to_dict


def test_fate_deck_is_deterministic_for_same_ids():
    a = build_fate_deck("battle-x", "spirit-1")
    b = build_fate_deck("battle-x", "spirit-1")
    assert a == b


def test_fate_deck_differs_across_spirits():
    a = build_fate_deck("battle-x", "spirit-1")
    b = build_fate_deck("battle-x", "spirit-2")
    assert a != b


def test_card_draw_and_return_are_reproducible():
    def run() -> tuple[list[str], list[str]]:
        state = CardState(deck=build_fate_deck("b", "s"))
        drawn = [draw_card(state, "b", "s") for _ in range(3)]
        return_card_to_deck(state, drawn[0], "b", "s")
        return drawn, list(state.deck)

    assert run() == run()


def test_random_source_is_deterministic_and_domain_scoped():
    a = RandomSource("seed-1", {})
    b = RandomSource("seed-1", {})
    seq_a = [a.next("crit").random() for _ in range(5)]
    seq_b = [b.next("crit").random() for _ in range(5)]
    assert seq_a == seq_b

    # Each domain advances an independent counter.
    counters: dict[str, int] = {}
    src = RandomSource("seed-1", counters)
    src.next("crit")
    src.next("crit")
    src.next("target")
    assert counters == {"crit": 2, "target": 1}


def test_random_source_resumes_from_serialized_counters():
    # Same seed but a resumed counter must continue the stream, not restart it.
    fresh = RandomSource("s", {})
    first_three = [fresh.next("d").random() for _ in range(3)]

    resumed = RandomSource("s", {"d": 2})
    assert resumed.next("d").random() == first_three[2]


def test_seeded_random_matches_legacy_card_seed_format():
    # Guifashi save-compat: the shared helper must reproduce the old seed string.
    import random

    legacy = random.Random("battle:spirit:draw:3")
    shared = seeded_random("battle", "spirit", "draw", 3)
    assert [legacy.random() for _ in range(4)] == [shared.random() for _ in range(4)]


def test_state_roundtrip_preserves_rng_fields(standard_engine):
    standard_engine.next_rng("crit")
    standard_engine.next_rng("crit")
    raw = state_to_dict(standard_engine.state)
    assert raw["rngSeed"] == standard_engine.state.rng_seed
    assert raw["rngCounters"] == {"crit": 2}
    restored = state_from_dict(raw)
    assert restored.rng_seed == standard_engine.state.rng_seed
    assert restored.rng_counters == {"crit": 2}


def test_scripted_battle_state_roundtrips(standard_engine):
    for _ in range(12):
        if standard_engine.state.phase == BattlePhase.finished:
            break
        assert skip_active(standard_engine)

    raw = state_to_dict(standard_engine.state)
    restored = state_from_dict(deepcopy(raw))
    # Normalized serialization is a stable fixed point: once a snapshot has been
    # through one decode/encode cycle, further round-trips must not drift.
    normalized = state_to_dict(restored)
    assert state_to_dict(state_from_dict(deepcopy(normalized))) == normalized

    assert restored.action_count == standard_engine.state.action_count
    assert restored.active_actor_id == standard_engine.state.active_actor_id
    for pid in (P1, P2):
        assert [s.unique_id for s in restored.players[pid].spirits] == [
            s.unique_id for s in standard_engine.state.players[pid].spirits
        ]
