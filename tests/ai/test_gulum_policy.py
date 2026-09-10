from __future__ import annotations

from tests.conftest import P1, by_template, make_engine
from roco.core.ai.policies.extended import GulumPolicy
from roco.core.battle.types import ActionType, EffectType
from roco.core.battle.utils import make_effect


def test_gulum_casts_shengen_when_missing_and_affordable():
    engine = make_engine(
        ("gulum", "flora", "clawdragon", "chaosling", "tita"),
        ("qiuka", "fanying", "steamdragon", "guifashi", "cuiding"),
    )
    gulum = by_template(engine, P1, "gulum")
    engine.state.players[P1].team_energy = 4
    policy = GulumPolicy()

    shengen = {
        "type": ActionType.use_skill.value,
        "skillId": "gulum_skill2",
        "actorId": gulum.unique_id,
        "playerId": P1,
    }
    gather = {
        "type": ActionType.gather_energy.value,
        "actorId": gulum.unique_id,
        "playerId": P1,
    }
    assert policy.score(engine, gulum, shengen) > policy.score(engine, gulum, gather)


def test_gulum_gathers_when_shengen_fresh():
    engine = make_engine(
        ("gulum", "flora", "clawdragon", "chaosling", "tita"),
        ("qiuka", "fanying", "steamdragon", "guifashi", "cuiding"),
    )
    gulum = by_template(engine, P1, "gulum")
    engine.state.players[P1].team_energy = 10
    gulum.effects.append(
        make_effect(
            EffectType.state_shengen,
            gulum.unique_id,
            duration_turns=3,
            display_name="深根",
        )
    )
    policy = GulumPolicy()

    shengen = {
        "type": ActionType.use_skill.value,
        "skillId": "gulum_skill2",
        "actorId": gulum.unique_id,
        "playerId": P1,
    }
    gather = {
        "type": ActionType.gather_energy.value,
        "actorId": gulum.unique_id,
        "playerId": P1,
    }
    assert policy.score(engine, gulum, gather) > policy.score(engine, gulum, shengen)


def test_gulum_refreshes_shengen_when_one_turn_left():
    engine = make_engine(
        ("gulum", "flora", "clawdragon", "chaosling", "tita"),
        ("qiuka", "fanying", "steamdragon", "guifashi", "cuiding"),
    )
    gulum = by_template(engine, P1, "gulum")
    engine.state.players[P1].team_energy = 4
    gulum.effects.append(
        make_effect(
            EffectType.state_shengen,
            gulum.unique_id,
            duration_turns=1,
            display_name="深根",
        )
    )
    policy = GulumPolicy()

    shengen = {
        "type": ActionType.use_skill.value,
        "skillId": "gulum_skill2",
        "actorId": gulum.unique_id,
        "playerId": P1,
    }
    gather = {
        "type": ActionType.gather_energy.value,
        "actorId": gulum.unique_id,
        "playerId": P1,
    }
    assert policy.score(engine, gulum, shengen) > policy.score(engine, gulum, gather)
