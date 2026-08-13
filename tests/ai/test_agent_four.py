from __future__ import annotations

from roco.core.ai import choose_action
from roco.core.ai.legal import enumerate_legal_actions
from roco.core.battle.types import ActionType
from tests.conftest import advance_to, by_template, make_engine


def _force_active(engine, template_id: str, player_id: str = "p1"):
    actor = by_template(engine, player_id, template_id)
    advance_to(engine, actor)
    return actor


def test_enumerate_includes_basics_for_flora():
    engine = make_engine(("flora",) * 5, ("flora",) * 5)
    actor = _force_active(engine, "flora")
    actions = enumerate_legal_actions(engine, actor.owner_id)
    types = {a["type"] for a in actions}
    assert ActionType.normal_attack.value in types
    assert ActionType.gather_energy.value in types
    assert ActionType.use_skill.value in types
    skills = {a.get("skillId") for a in actions if a["type"] == ActionType.use_skill.value}
    assert "flora_skill1" in skills
    assert "flora_skill3" in skills


def test_flora_heals_low_ally():
    engine = make_engine(("flora", "clawdragon") + ("flora",) * 3, ("flora",) * 5)
    flora = by_template(engine, "p1", "flora")
    ally = by_template(engine, "p1", "clawdragon")
    ally.current_hp = max(1, ally.base_stats.hp // 5)
    engine.state.players["p1"].team_energy = 10
    advance_to(engine, flora)
    action = choose_action(engine, "p1")
    assert action["type"] == ActionType.use_skill.value
    assert action["skillId"] == "flora_skill1"
    assert action.get("targetId") == ally.unique_id


def test_clawdragon_opens_with_dance_when_affordable():
    engine = make_engine(("clawdragon",) * 5, ("flora",) * 5)
    dragon = _force_active(engine, "clawdragon")
    engine.state.players["p1"].team_energy = 10
    action = choose_action(engine, "p1")
    assert action["type"] == ActionType.use_skill.value
    assert action["skillId"] == "clawdragon_skill2"
    assert engine.submit_action("p1", action)


def test_starweaver_pulses_when_low_personal_energy():
    engine = make_engine(("starweaver",) * 5, ("flora",) * 5)
    cat = _force_active(engine, "starweaver")
    cat.energy = 1
    action = choose_action(engine, "p1")
    assert action["type"] == ActionType.use_skill.value
    assert action["skillId"] == "starweaver_skill1"


def test_steamdragon_brands_when_has_energy():
    engine = make_engine(("steamdragon",) * 5, ("flora",) * 5)
    steam = _force_active(engine, "steamdragon")
    engine.state.players["p1"].team_energy = 10
    action = choose_action(engine, "p1")
    assert action["type"] == ActionType.use_skill.value
    assert action["skillId"] == "steamdragon_skill1"
    assert action.get("targetId")
    assert engine.submit_action("p1", action)


def test_ai_can_play_several_turns_without_illegal():
    engine = make_engine(
        ("flora", "clawdragon", "starweaver", "steamdragon", "flora"),
        ("flora",) * 5,
    )
    for _ in range(12):
        if engine.state.phase.value == "finished":
            break
        actor_id = engine.state.active_actor_id
        assert actor_id
        actor = engine.find_spirit_anywhere(actor_id)
        assert actor
        action = choose_action(engine, actor.owner_id)
        assert engine.submit_action(actor.owner_id, action)
