from __future__ import annotations

import pytest

from roco.core.battle.timeline import (
    ACTION_GAP,
    action_value,
    adjust_charge_advance,
    adjust_charge_delay,
    compute_timeline_preview,
    pick_next_actor,
)


@pytest.mark.parametrize(
    ("charge", "speed", "expected"),
    [(10000, 250, 40.0), (5000, 100, 50.0), (10000, 0, float("inf"))],
)
def test_action_value_is_charge_divided_by_speed(charge, speed, expected):
    assert action_value(charge, speed) == expected


def test_pick_next_actor_tie_breaks_by_speed_then_id():
    entries = [
        ("slow", 1000.0, 100, "b"),
        ("fast", 2000.0, 200, "c"),
        ("same_fast_lower_id", 2000.0, 200, "a"),
    ]

    assert pick_next_actor(entries) == "same_fast_lower_id"


def test_advance_and_delay_adjust_charge_by_gap_percent():
    assert adjust_charge_advance(ACTION_GAP, 0.24) == 7600.0
    assert adjust_charge_advance(1000, 0.24) == 0.0
    assert adjust_charge_delay(1000, 0.24) == 3400.0


def test_preview_simulates_without_mutating_source_objects():
    spirits = [
        {"id": "a", "charge": 10000.0, "speed": 100},
        {"id": "b", "charge": 10000.0, "speed": 200},
        {"id": "c", "charge": 5000.0, "speed": 100},
    ]
    before = [dict(s) for s in spirits]

    preview = compute_timeline_preview(
        spirits,
        lambda s: s["charge"],
        lambda s: s["speed"],
        lambda s: s["id"],
        count=4,
    )

    assert [s["id"] for s in preview] == ["b", "c", "b", "a"]
    assert spirits == before
