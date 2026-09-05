"""Unit tests for desktop combat FX log parsing."""

from __future__ import annotations

from roco.apps.desktop.combat_fx import float_steps_from_logs
from roco.core.battle.types import BattleLogEntry, BattleLogType


def test_float_steps_damage_and_heal_ordered() -> None:
    logs = [
        BattleLogEntry(
            BattleLogType.action_executed,
            1,
            "acted",
            {"actorId": "a"},
        ),
        BattleLogEntry(
            BattleLogType.damage_dealt,
            1,
            "hit",
            {"attackerId": "a", "targetId": "b", "damage": 42},
        ),
        BattleLogEntry(
            BattleLogType.heal_applied,
            1,
            "heal",
            {"actorId": "a", "targetId": "a", "heal": 7},
        ),
        BattleLogEntry(
            BattleLogType.damage_dealt,
            1,
            "dot",
            {"attackerId": None, "targetId": "b", "damage": 3},
        ),
    ]
    steps = float_steps_from_logs(logs)
    assert [(s.spirit_id, s.kind, s.amount) for s in steps] == [
        ("b", "damage", 42),
        ("a", "heal", 7),
        ("b", "damage", 3),
    ]


def test_float_steps_skips_incomplete_data() -> None:
    logs = [
        BattleLogEntry(BattleLogType.damage_dealt, 1, "x", None),
        BattleLogEntry(BattleLogType.damage_dealt, 1, "y", {"damage": 9}),
        BattleLogEntry(BattleLogType.heal_applied, 1, "z", {"targetId": "t", "heal": 0}),
        BattleLogEntry(BattleLogType.heal_applied, 1, "ok", {"targetId": "t", "heal": 4}),
    ]
    steps = float_steps_from_logs(logs)
    assert len(steps) == 1
    assert steps[0].amount == 4


def test_float_steps_passive_heal_like_emergency_support() -> None:
    logs = [
        BattleLogEntry(
            BattleLogType.damage_dealt,
            1,
            "hit",
            {"attackerId": "e", "targetId": "ally", "damage": 80},
        ),
        BattleLogEntry(
            BattleLogType.passive_triggered,
            1,
            "紧急支援",
            {"floraId": "flora", "actorId": "flora", "targetId": "ally"},
        ),
        BattleLogEntry(
            BattleLogType.heal_applied,
            1,
            "heal",
            {"actorId": "flora", "targetId": "ally", "heal": 120},
        ),
    ]
    steps = float_steps_from_logs(logs)
    assert [(s.spirit_id, s.kind, s.amount) for s in steps] == [
        ("ally", "damage", 80),
        ("ally", "heal", 120),
    ]
