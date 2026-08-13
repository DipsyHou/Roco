from __future__ import annotations

import copy

from tests.conftest import P1, P2, by_template, cast_skill, effects_of, skip_active, submit
from roco.core.battle.effects import apply_infusion, make_effect
from roco.core.battle.timeline import ACTION_GAP
from roco.core.battle.types import ActionType, BaseStats, EffectType, StatType
from roco.core.battle.engine import BattleEngine
from roco.core.spirits import get_spirit_template
from roco.core.spirits.guifashi_cards import CardState


def _layout_adjacent(engine):
    cuiding = by_template(engine, P1, "cuiding")
    claw = by_template(engine, P1, "clawdragon")
    flora = by_template(engine, P1, "flora")
    chaos = by_template(engine, P1, "chaosling")
    starweaver = by_template(engine, P1, "starweaver")
    starweaver.slot = 1
    flora.slot = 2
    chaos.slot = 3
    claw.slot = 4
    cuiding.slot = 5
    return cuiding, claw, flora, chaos


def test_warm_current_heals_anchor_and_adjacent_only(engine_factory):
    engine = engine_factory(
        ("cuiding", "clawdragon", "flora", "chaosling", "starweaver"),
        ("qiuka", "fanying", "tita", "guifashi", "steamdragon"),
    )
    cuiding, claw, flora, chaos = _layout_adjacent(engine)
    for spirit in (cuiding, claw, flora, chaos):
        spirit.current_hp -= 50
    hp_before = {
        spirit.unique_id: spirit.current_hp
        for spirit in (claw, flora, chaos, cuiding)
    }

    assert cast_skill(engine, cuiding, "cuiding_skill1", flora)

    assert flora.current_hp > hp_before[flora.unique_id]
    assert chaos.current_hp > hp_before[chaos.unique_id]
    assert claw.current_hp == hp_before[claw.unique_id]
    assert effects_of(flora, EffectType.buff_infusion)
    assert effects_of(chaos, EffectType.buff_infusion)
    assert not effects_of(claw, EffectType.buff_infusion)


def test_chenjing_grants_energy_when_target_already_infused(engine_factory):
    engine = engine_factory(
        ("cuiding", "clawdragon", "flora", "chaosling", "starweaver"),
        ("qiuka", "fanying", "tita", "guifashi", "steamdragon"),
    )
    cuiding, _, flora, _ = _layout_adjacent(engine)
    apply_infusion(flora, cuiding.unique_id, duration_turns=3)
    energy_before = engine.state.players[P1].team_energy
    hp_before = flora.current_hp

    assert cast_skill(engine, cuiding, "cuiding_skill1", flora)

    assert flora.current_hp == hp_before
    assert engine.state.players[P1].team_energy == energy_before - 3 + 1


def test_chenjing_grants_infusion_when_teammate_not_infused(engine_factory):
    engine = engine_factory(
        ("cuiding", "clawdragon", "flora", "chaosling", "starweaver"),
        ("qiuka", "fanying", "tita", "guifashi", "steamdragon"),
    )
    cuiding, _, flora, chaos = _layout_adjacent(engine)
    flora.current_hp -= 80
    chaos.current_hp -= 80
    apply_infusion(flora, cuiding.unique_id, duration_turns=3)
    energy_before = engine.state.players[P1].team_energy

    assert cast_skill(engine, cuiding, "cuiding_skill1", flora)

    assert engine.state.players[P1].team_energy == energy_before - 3 + 1
    assert effects_of(flora, EffectType.buff_infusion)
    assert effects_of(chaos, EffectType.buff_infusion)


def test_ripple_damages_enemies_and_dispels_buff(engine_factory):
    engine = engine_factory(
        ("cuiding", "clawdragon", "flora", "chaosling", "starweaver"),
        ("qiuka", "fanying", "tita", "guifashi", "steamdragon"),
    )
    cuiding = by_template(engine, P1, "cuiding")
    enemy = engine.get_active_spirits(P2)[0]
    enemy.effects.append(
        make_effect(
            EffectType.buff_stat_percent_boost,
            "x",
            duration_turns=2,
            stat_type=StatType.speed,
            value=0.1,
        )
    )
    enemy_hp_before = enemy.current_hp

    assert cast_skill(engine, cuiding, "cuiding_skill2")

    assert enemy.current_hp < enemy_hp_before
    assert not effects_of(enemy, EffectType.buff_stat_percent_boost)


def test_dance_heals_self_and_teammates(engine_factory):
    engine = engine_factory(
        ("cuiding", "clawdragon", "flora", "chaosling", "starweaver"),
        ("qiuka", "fanying", "tita", "guifashi", "steamdragon"),
    )
    cuiding = by_template(engine, P1, "cuiding")
    teammates = [
        spirit
        for spirit in engine.get_active_spirits(P1)
        if spirit.unique_id != cuiding.unique_id
    ]
    for spirit in teammates:
        spirit.current_hp -= 60
    cuiding.current_hp -= 60
    hp_before = {spirit.unique_id: spirit.current_hp for spirit in teammates}
    cuiding_hp_before = cuiding.current_hp

    assert cast_skill(engine, cuiding, "cuiding_skill3")

    assert cuiding.current_hp > cuiding_hp_before
    assert effects_of(cuiding, EffectType.buff_infusion)
    for teammate in teammates:
        assert teammate.current_hp > hp_before[teammate.unique_id]
        assert effects_of(teammate, EffectType.buff_infusion)
    first_in_slot = min(teammates, key=lambda spirit: spirit.slot)
    assert engine.state.active_actor_id == first_in_slot.unique_id


def test_dance_extra_turns_follow_slot_order(engine_factory):
    engine = engine_factory(
        ("cuiding", "clawdragon", "flora", "chaosling", "starweaver"),
        ("qiuka", "fanying", "tita", "guifashi", "steamdragon"),
    )
    cuiding, claw, flora, chaos = _layout_adjacent(engine)
    starweaver = by_template(engine, P1, "starweaver")
    ordered = sorted(
        [starweaver, flora, chaos, claw],
        key=lambda spirit: spirit.slot,
    )

    assert cast_skill(engine, cuiding, "cuiding_skill3")
    for ally in ordered:
        assert engine.state.active_actor_id == ally.unique_id
        assert skip_active(engine)


def test_dance_extra_action_does_not_touch_timeline_or_turn_hooks():
    engine = BattleEngine(
        "sim",
        P1,
        P2,
        [get_spirit_template("cuiding"), get_spirit_template("steamdragon")],
        [get_spirit_template("fanying")],
    )
    cuiding = by_template(engine, P1, "cuiding")
    steam = by_template(engine, P1, "steamdragon")
    cuiding.effects.append(
        make_effect(EffectType.buff_damage_percent_boost, cuiding.unique_id, duration_turns=1)
    )

    while engine.state.active_actor_id != cuiding.unique_id:
        skip_active(engine)

    engine.ensure_active_turn_begun()
    engine.submit_action(
        P1,
        {
            "type": ActionType.use_skill.value,
            "playerId": P1,
            "actorId": cuiding.unique_id,
            "skillId": "cuiding_skill3",
        },
    )

    assert engine.state.active_actor_id == steam.unique_id
    slot = engine.current_extra_slot()
    assert slot is not None and slot.source == "dance"
    assert slot.policy_id == "cuiding_dance"
    action_count_after_dance = engine.state.action_count
    assert effects_of(cuiding, EffectType.buff_damage_percent_boost)

    engine.submit_action(
        P1,
        {"type": ActionType.skip.value, "playerId": P1, "actorId": steam.unique_id},
    )

    assert engine.current_extra_slot() is None
    assert engine.state.action_count == action_count_after_dance + 1
    assert not effects_of(cuiding, EffectType.buff_damage_percent_boost)


def test_dance_extra_action_can_chain_guifashi_card_extra_action():
    engine = BattleEngine(
        "sim",
        P1,
        P2,
        [get_spirit_template("cuiding"), get_spirit_template("guifashi")],
        [get_spirit_template("fanying")],
    )
    cuiding = by_template(engine, P1, "cuiding")
    guifashi = by_template(engine, P1, "guifashi")
    guifashi.card_state = CardState(deck=["moon", "star"], hand=[]).to_dict()

    while engine.state.active_actor_id != cuiding.unique_id:
        skip_active(engine)

    engine.ensure_active_turn_begun()
    assert cast_skill(engine, cuiding, "cuiding_skill3")

    assert engine.state.active_actor_id == guifashi.unique_id
    dance_slot = engine.current_extra_slot()
    assert dance_slot is not None and dance_slot.source == "dance"
    assert dance_slot.policy_id == "cuiding_dance"
    action_count_after_dance = engine.state.action_count

    assert submit(engine, guifashi, ActionType.use_skill.value, skillId="guifashi_draw")

    chain_slot = engine.current_extra_slot()
    assert chain_slot is not None
    assert chain_slot.actor_id == guifashi.unique_id
    assert chain_slot.policy_id == "guifashi_chain"
    assert engine.state.action_count == action_count_after_dance
    assert CardState.from_dict(guifashi.card_state).hand

    assert submit(engine, guifashi, ActionType.skip.value)

    assert engine.current_extra_slot() is None
    assert engine.state.action_count == action_count_after_dance + 1


def test_dance_extra_action_can_gather_energy():
    engine = BattleEngine(
        "sim",
        P1,
        P2,
        [get_spirit_template("cuiding"), get_spirit_template("steamdragon")],
        [get_spirit_template("fanying")],
    )
    cuiding = by_template(engine, P1, "cuiding")
    steam = by_template(engine, P1, "steamdragon")

    while engine.state.active_actor_id != cuiding.unique_id:
        skip_active(engine)

    engine.ensure_active_turn_begun()
    assert cast_skill(engine, cuiding, "cuiding_skill3")
    assert engine.state.active_actor_id == steam.unique_id

    energy_before = engine.state.players[P1].team_energy
    assert submit(engine, steam, ActionType.gather_energy.value)
    assert engine.state.players[P1].team_energy > energy_before


def test_dance_delay_pushes_back_first_normal_turn_not_second():
    fanying_tpl = copy.deepcopy(get_spirit_template("fanying"))
    assert fanying_tpl is not None
    bs = fanying_tpl.base_stats
    # 凡鹰显著更快，才能稳定测「共舞延后后敌方先于 steam 正常回合」。
    fanying_tpl.base_stats = BaseStats(
        hp=bs.hp, atk=bs.atk, mag_atk=bs.mag_atk, def_=bs.def_, mag_def=bs.mag_def, speed=200
    )
    engine = BattleEngine(
        "sim",
        P1,
        P2,
        [get_spirit_template("cuiding"), get_spirit_template("steamdragon")],
        [fanying_tpl],
    )
    cuiding = by_template(engine, P1, "cuiding")
    steam = by_template(engine, P1, "steamdragon")

    while engine.state.active_actor_id != cuiding.unique_id:
        skip_active(engine)

    engine.ensure_active_turn_begun()
    charge_before_dance = steam.charge
    engine.submit_action(
        P1,
        {
            "type": ActionType.use_skill.value,
            "playerId": P1,
            "actorId": cuiding.unique_id,
            "skillId": "cuiding_skill3",
        },
    )

    assert steam.charge == charge_before_dance + ACTION_GAP * 0.50

    engine.submit_action(
        P1,
        {"type": ActionType.skip.value, "playerId": P1, "actorId": steam.unique_id},
    )

    assert engine.state.active_actor_id != steam.unique_id

    steps_until_steam = 0
    for _ in range(50):
        if engine.state.active_actor_id == steam.unique_id:
            break
        assert skip_active(engine)
        steps_until_steam += 1

    assert steps_until_steam > 0
