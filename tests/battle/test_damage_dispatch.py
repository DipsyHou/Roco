from __future__ import annotations

import pytest

from roco.core.battle.events import DamageEvent, DamageSource, dispatch_damage
from roco.core.spirit_logic import SpiritLogic
from roco.core.spirits import registry
from tests.conftest import P1, P2, by_template


class RecordingLogic(SpiritLogic):
    def __init__(self, template_id: str, events: list[tuple[str, str, DamageSource]]) -> None:
        self.template_id = template_id
        self.events = events

    def on_damage(self, ctx, spirit, event):  # noqa: ANN001
        self.events.append(("damage", spirit.unique_id, event.source))

    def on_ally_damage_dealt(self, ctx, observer, event):  # noqa: ANN001
        self.events.append(("ally", observer.unique_id, event.source))

    def on_attack_hit(self, ctx, player_id, actor, target, damage):  # noqa: ANN001
        self.events.append(("hit", actor.unique_id, DamageSource.attack))


def test_damage_dispatch_runs_on_damage_before_ally_hooks(monkeypatch, engine_factory):
    order: list[str] = []

    class RecordingClawdragon(SpiritLogic):
        template_id = "clawdragon"

        def on_damage(self, ctx, spirit, event):  # noqa: ANN001
            if spirit.template_id == "clawdragon" and event.target.unique_id == spirit.unique_id:
                order.append("on_damage")

    class RecordingStarweaver(SpiritLogic):
        template_id = "starweaver"

        def on_ally_damage_dealt(self, ctx, observer, event):  # noqa: ANN001
            if observer.template_id == "starweaver":
                order.append("on_ally_damage_dealt")

    monkeypatch.setitem(registry._REGISTRY, "clawdragon", RecordingClawdragon())
    monkeypatch.setitem(registry._REGISTRY, "starweaver", RecordingStarweaver())
    engine = engine_factory(
        ("qiuka", "starweaver", "flora", "chaosling", "tita"),
        ("clawdragon", "flora", "chaosling", "tita", "fanying"),
    )
    attacker = by_template(engine, P1, "qiuka")
    target = by_template(engine, P2, "clawdragon")

    dispatch_damage(engine, DamageEvent(attacker, target, 10, source=DamageSource.skill))

    assert order == ["on_damage", "on_ally_damage_dealt"]


@pytest.mark.parametrize(
    ("source", "triggers_hit"),
    [
        (DamageSource.attack, True),
        (DamageSource.skill, True),
        (DamageSource.dot, False),
        (DamageSource.fixed, False),
        (DamageSource.other, False),
    ],
)
def test_damage_dispatch_filters_attack_hit_by_source(monkeypatch, engine_factory, source, triggers_hit):
    events: list[tuple[str, str, DamageSource]] = []
    monkeypatch.setitem(registry._REGISTRY, "flora", RecordingLogic("flora", events))
    monkeypatch.setitem(registry._REGISTRY, "qiuka", RecordingLogic("qiuka", events))
    engine = engine_factory(("flora",) * 5, ("qiuka",) * 5)
    attacker = engine.get_all_spirits("p1")[0]
    target = engine.get_all_spirits("p2")[0]

    dispatch_damage(engine, DamageEvent(attacker, target, 10, source=source))

    assert any(kind == "damage" for kind, _, _ in events)
    assert any(kind == "ally" for kind, _, _ in events)
    assert any(kind == "hit" for kind, _, _ in events) is triggers_hit


def test_damage_dispatch_runs_on_zero_damage_segment(monkeypatch, engine_factory):
    events: list[tuple[str, str, DamageSource]] = []
    monkeypatch.setitem(registry._REGISTRY, "flora", RecordingLogic("flora", events))
    monkeypatch.setitem(registry._REGISTRY, "qiuka", RecordingLogic("qiuka", events))
    engine = engine_factory(("flora",) * 5, ("qiuka",) * 5)
    attacker = engine.get_all_spirits("p1")[0]
    target = engine.get_all_spirits("p2")[0]

    dispatch_damage(engine, DamageEvent(attacker, target, 0, source=DamageSource.attack))

    assert any(kind == "damage" for kind, _, _ in events)
    assert any(kind == "ally" for kind, _, _ in events)
    assert any(kind == "hit" for kind, _, _ in events)
