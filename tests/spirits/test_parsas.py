from __future__ import annotations

from tests.conftest import P1, P2, by_template, cast_skill, normal_attack


def test_opening_energy_is_two(engine_factory):
    engine = engine_factory(
        ("parsas", "flora", "clawdragon", "chaosling", "tita"),
        ("qiuka", "fanying", "steamdragon", "guifashi", "cuiding"),
    )
    assert by_template(engine, P1, "parsas").energy == 2


def test_contract_costs_10_percent_hp_and_grants_3_plus_sole_target(engine_factory):
    engine = engine_factory(
        ("parsas", "flora", "clawdragon", "chaosling", "tita"),
        ("qiuka", "fanying", "steamdragon", "guifashi", "cuiding"),
    )
    parsas = by_template(engine, P1, "parsas")
    before_hp = parsas.current_hp
    parsas.energy = 0

    assert cast_skill(engine, parsas, "parsas_skill1")

    assert before_hp - parsas.current_hp == int(before_hp * 0.10)
    # 契约 +3，自身为唯一目标再 +2
    assert parsas.energy == 5


def test_sole_target_from_enemy_normal_attack(engine_factory):
    engine = engine_factory(
        ("parsas", "flora", "clawdragon", "chaosling", "tita"),
        ("qiuka", "fanying", "steamdragon", "guifashi", "cuiding"),
    )
    parsas = by_template(engine, P1, "parsas")
    enemy = by_template(engine, P2, "qiuka")
    parsas.energy = 5
    engine.state.active_actor_id = enemy.unique_id
    engine.state.turn_prepared_actor_id = enemy.unique_id

    assert normal_attack(engine, enemy, parsas)
    assert parsas.energy == 7


def test_aoe_skill_does_not_count_as_sole_target(engine_factory):
    engine = engine_factory(
        ("parsas", "flora", "clawdragon", "chaosling", "tita"),
        ("chaosling", "fanying", "steamdragon", "guifashi", "cuiding"),
    )
    parsas = by_template(engine, P1, "parsas")
    chaos = by_template(engine, P2, "chaosling")
    parsas.energy = 5
    engine.state.active_actor_id = chaos.unique_id
    engine.state.turn_prepared_actor_id = chaos.unique_id

    assert cast_skill(engine, chaos, "chaosling_skill2")
    assert parsas.energy == 5


def test_troll_eye_costs_seven(engine_factory):
    engine = engine_factory(
        ("parsas", "flora", "clawdragon", "chaosling", "tita"),
        ("qiuka", "fanying", "steamdragon", "guifashi", "cuiding"),
    )
    parsas = by_template(engine, P1, "parsas")
    enemy = by_template(engine, P2, "qiuka")
    parsas.energy = 7

    assert cast_skill(engine, parsas, "parsas_skill2", enemy)
    assert parsas.energy == 0
    from roco.core.battle.types import EffectType
    from tests.conftest import effects_of

    # 本回合行动结束会扣 1 层持续，落地后可见为 2
    terror = effects_of(parsas, EffectType.buff_def_pierce)[0]
    assert terror.duration_turns == 2


def test_crossing_threshold_extends_terror(engine_factory):
    from roco.core.battle.types import EffectType
    from tests.conftest import effects_of

    engine = engine_factory(
        ("parsas", "flora", "clawdragon", "chaosling", "tita"),
        ("qiuka", "fanying", "steamdragon", "guifashi", "cuiding"),
    )
    parsas = by_template(engine, P1, "parsas")
    enemy = by_template(engine, P2, "qiuka")
    parsas.energy = 7
    assert cast_skill(engine, parsas, "parsas_skill2", enemy)
    assert effects_of(parsas, EffectType.buff_def_pierce)[0].duration_turns == 2

    parsas.energy = 12
    engine.state.active_actor_id = enemy.unique_id
    engine.state.turn_prepared_actor_id = enemy.unique_id
    assert normal_attack(engine, enemy, parsas)
    assert parsas.energy >= 13
    assert effects_of(parsas, EffectType.buff_def_pierce)[0].duration_turns == 3
    assert any(
        e.type.value == "passive_triggered" and "收藏灵魂" in e.message
        for e in engine.state.battle_log
    )