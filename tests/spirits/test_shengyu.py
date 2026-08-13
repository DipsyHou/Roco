"""圣域祭司 — 月盈秘能放大等。"""

from __future__ import annotations

from tests.conftest import P1, by_template, cast_skill


def test_moon_gain_bonus_on_opening_energy(engine_factory):
    """开局获得秘能也吃月盈：帕尔萨斯 2→3，黑猫 4→5。"""
    with_priest = engine_factory(
        ("parsas", "starweaver", "shengyu", "flora", "tita"),
        ("clawdragon", "flora", "chaosling", "steamdragon", "fanying"),
    )
    assert by_template(with_priest, P1, "parsas").energy == 3
    assert by_template(with_priest, P1, "starweaver").energy == 5

    without_priest = engine_factory(
        ("parsas", "starweaver", "flora", "chaosling", "tita"),
        ("clawdragon", "flora", "chaosling", "steamdragon", "fanying"),
    )
    assert by_template(without_priest, P1, "parsas").energy == 2
    assert by_template(without_priest, P1, "starweaver").energy == 4


def test_moon_gain_bonus_on_starweaver_burst(engine_factory):
    """星爆回能走统一入口，有祭司时 4→5。"""
    engine = engine_factory(
        ("starweaver", "shengyu", "flora", "tita", "fanying"),
        ("clawdragon", "flora", "chaosling", "steamdragon", "tita"),
    )
    star = by_template(engine, P1, "starweaver")
    star.energy = 6

    assert cast_skill(engine, star, "starweaver_skill3")
    assert star.energy == 5
    assert any("获得5点秘能" in e.message for e in engine.state.battle_log)


def test_moon_gain_bonus_on_parsas_sole_target(engine_factory):
    """帕尔萨斯成为唯一目标 +2 也吃月盈 → 实际 +3。"""
    from tests.conftest import P2, normal_attack

    engine = engine_factory(
        ("parsas", "shengyu", "flora", "tita", "fanying"),
        ("clawdragon", "flora", "chaosling", "steamdragon", "tita"),
    )
    parsas = by_template(engine, P1, "parsas")
    enemy = by_template(engine, P2, "clawdragon")
    parsas.energy = 5
    engine.state.active_actor_id = enemy.unique_id
    engine.state.turn_prepared_actor_id = enemy.unique_id

    assert normal_attack(engine, enemy, parsas)
    assert parsas.energy == 8


def test_blessing_grants_amplified_energy(engine_factory):
    """圣洁给目标 1 点秘能，再被月盈放大为实际获得 2 点。"""
    engine = engine_factory(
        ("shengyu", "parsas", "flora", "tita", "fanying"),
        ("clawdragon", "flora", "chaosling", "steamdragon", "tita"),
    )
    priest = by_template(engine, P1, "shengyu")
    parsas = by_template(engine, P1, "parsas")

    assert cast_skill(engine, priest, "shengyu_skill1", parsas)
    assert any("额外回复了2点秘能" in e.message for e in engine.state.battle_log)
