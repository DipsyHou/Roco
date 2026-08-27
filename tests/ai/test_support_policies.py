from __future__ import annotations

from roco.core.ai import choose_action
from roco.core.ai import features as F
from roco.core.battle.types import ActionType
from tests.conftest import advance_to, by_template, make_engine


def _active(engine, template_id: str, player_id: str = "p1"):
    actor = by_template(engine, player_id, template_id)
    advance_to(engine, actor)
    return actor


def test_main_c_heuristic_prefers_high_offense_carry():
    engine = make_engine(("flora", "clawdragon", "steamdragon", "starweaver", "flora"), ("flora",) * 5)
    main_c = F.main_c_ally(engine, "p1")
    assert main_c is not None
    assert main_c.template_id == "clawdragon"


def test_flora_heals_low_hp_ally():
    engine = make_engine(("flora", "clawdragon", "steamdragon", "starweaver", "flora"), ("flora",) * 5)
    flora = _active(engine, "flora")
    ally = by_template(engine, "p1", "clawdragon")
    ally.current_hp = ally.max_hp // 3
    engine.state.players["p1"].team_energy = 8

    action = choose_action(engine, "p1")

    assert action["type"] == ActionType.use_skill.value
    assert action["skillId"] == "flora_skill1"
    assert action["targetId"] == ally.unique_id


def test_flora_gives_antires_to_main_c_when_team_is_stable():
    engine = make_engine(("flora", "clawdragon", "steamdragon", "starweaver", "flora"), ("flora",) * 5)
    flora = _active(engine, "flora")
    main_c = F.main_c_ally(engine, "p1")
    assert main_c is not None and main_c.template_id == "clawdragon"
    engine.state.players["p1"].team_energy = 8

    action = choose_action(engine, "p1")

    assert action["type"] == ActionType.use_skill.value
    assert action["skillId"] == "flora_skill2"
    assert action["targetId"] == main_c.unique_id


def test_flora_uses_anesthesia_when_energy_is_very_high():
    engine = make_engine(("flora", "clawdragon", "steamdragon", "starweaver", "flora"), ("flora",) * 5)
    flora = _active(engine, "flora")
    engine.state.players["p1"].team_energy = 10

    action = choose_action(engine, "p1")

    assert action["type"] == ActionType.use_skill.value
    assert action["skillId"] == "flora_skill3"


def test_jifangfang_shields_when_energy_is_sufficient():
    engine = make_engine(("jifangfang", "clawdragon", "steamdragon", "flora", "flora"), ("flora",) * 5)
    ff = _active(engine, "jifangfang")
    engine.state.players["p1"].team_energy = 4

    action = choose_action(engine, "p1")

    assert action["type"] == ActionType.use_skill.value
    assert action["skillId"] == "jifangfang_skill1"
    assert action["playerId"] == ff.owner_id


def test_cixiyi_sets_up_shields_when_energy_is_sufficient():
    engine = make_engine(("cixiyi", "clawdragon", "steamdragon", "flora", "flora"), ("flora",) * 5)
    cx = _active(engine, "cixiyi")
    engine.state.players["p1"].team_energy = 3

    action = choose_action(engine, "p1")

    assert action["type"] == ActionType.use_skill.value
    assert action["skillId"] == "cixiyi_skill1"
    assert action["playerId"] == cx.owner_id


def test_guifashi_does_not_pick_draw_when_energy_is_zero():
    """能量不足时占卜不得进入合法行动，否则人机会反复校验失败。"""
    from roco.core.ai.legal import enumerate_legal_actions

    engine = make_engine(
        ("guifashi", "flora", "clawdragon", "tita", "fanying"),
        ("flora",) * 5,
    )
    _active(engine, "guifashi")
    engine.state.players["p1"].team_energy = 0

    actions = enumerate_legal_actions(engine, "p1")
    assert all(a.get("skillId") != "guifashi_draw" for a in actions)

    action = choose_action(engine, "p1")
    assert engine.submit_action("p1", action) is True
