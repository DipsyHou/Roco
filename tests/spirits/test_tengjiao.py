from __future__ import annotations

from pytest import approx

from tests.conftest import P1, advance_to, by_template, cast_skill, effects_of, make_engine
from roco.core.battle.extra_action import ExtraActionSlot
from roco.core.battle.stats import get_effective_stat
from roco.core.battle.types import ActionType, BattlePhase, EffectType, StatType
from roco.core.spirits.tengjiao import (
    DISH_LAZIJI,
    DISH_MAOXUEWANG,
    DISH_SHUIZHUYU,
    FREE_POLICY_ID,
    _huoli_stacks,
    _pending_free,
    _set_huoli,
    _set_pending_free,
)


def _team():
    return ("tengjiao", "flora", "clawdragon", "chaosling", "starweaver")


def _force_free_dish(engine, tengjiao, dish: str) -> None:
    _set_pending_free(tengjiao, [dish])
    engine.queue_extra_actions(
        [
            ExtraActionSlot(
                actor_id=tengjiao.unique_id,
                policy_id=FREE_POLICY_ID,
                source=f"tengjiao_free:{dish}",
            )
        ],
        front=True,
    )
    engine._advance_to_next_extra_slot()
    engine.state.phase = BattlePhase.waiting_for_action


def _submit_serve(engine, tengjiao, target_id: str) -> bool:
    return engine.submit_action(
        P1,
        {
            "type": ActionType.use_skill.value,
            "playerId": P1,
            "actorId": tengjiao.unique_id,
            "skillId": "tengjiao_skill3",
            "targetId": target_id,
        },
    )


def test_ally_energy_spend_adds_huoli():
    engine = make_engine(_team())
    tengjiao = by_template(engine, P1, "tengjiao")
    flora = by_template(engine, P1, "flora")
    advance_to(engine, flora)
    before = _huoli_stacks(tengjiao)
    enemy = engine.get_active_spirits("p2")[0]
    assert cast_skill(engine, flora, "flora_skill1", enemy)
    assert _huoli_stacks(tengjiao) > before


def test_normal_attack_deals_damage():
    engine = make_engine(_team())
    tengjiao = by_template(engine, P1, "tengjiao")
    advance_to(engine, tengjiao)
    enemy = engine.get_active_spirits("p2")[0]
    before = enemy.current_hp
    assert engine.submit_action(
        P1,
        {
            "type": ActionType.normal_attack.value,
            "playerId": P1,
            "actorId": tengjiao.unique_id,
            "targetId": enemy.unique_id,
        },
    )
    assert enemy.current_hp < before


def test_oil_adds_huoli_and_atk_and_may_trigger_threshold():
    engine = make_engine(_team())
    tengjiao = by_template(engine, P1, "tengjiao")
    advance_to(engine, tengjiao)
    _set_huoli(tengjiao, 9)
    base = get_effective_stat(tengjiao, StatType.atk, exclude_conversion=True)
    assert cast_skill(engine, tengjiao, "tengjiao_skill1")
    # Resolve free chicken if queued
    while engine.state.extra_action_queue or (
        _pending_free(tengjiao)
        and engine.state.active_actor_id == tengjiao.unique_id
        and engine.current_extra_slot() is not None
    ):
        if engine.current_extra_slot() is None:
            break
        assert _submit_serve(engine, tengjiao, tengjiao.unique_id)
    assert _huoli_stacks(tengjiao) >= 14  # 9+2+5, possibly cleared if somehow 毛血旺
    oil = effects_of(tengjiao, EffectType.buff_stat_percent_boost)
    assert any(e.display_name == "浇油" for e in oil)
    assert get_effective_stat(tengjiao, StatType.atk, exclude_conversion=True) == approx(
        base * 1.2
    )


def test_laziji_conversion():
    engine = make_engine(_team())
    tengjiao = by_template(engine, P1, "tengjiao")
    flora = by_template(engine, P1, "flora")
    advance_to(engine, tengjiao)
    _force_free_dish(engine, tengjiao, DISH_LAZIJI)
    applier_atk = get_effective_stat(tengjiao, StatType.atk, exclude_conversion=True)
    assert _submit_serve(engine, tengjiao, flora.unique_id)
    assert effects_of(flora, EffectType.buff_laziji)
    expected = applier_atk * 0.10
    assert get_effective_stat(flora, StatType.atk) == approx(flora.base_stats.atk + expected)
    assert get_effective_stat(flora, StatType.mag_atk) == approx(
        flora.base_stats.mag_atk + expected
    )


def test_shuizhuyu_buffs_self_and_allies():
    engine = make_engine(_team())
    tengjiao = by_template(engine, P1, "tengjiao")
    flora = by_template(engine, P1, "flora")
    advance_to(engine, tengjiao)
    _force_free_dish(engine, tengjiao, DISH_SHUIZHUYU)
    base_atk = get_effective_stat(tengjiao, StatType.atk, exclude_conversion=True)
    assert _submit_serve(engine, tengjiao, tengjiao.unique_id)
    assert effects_of(tengjiao, EffectType.buff_shuizhuyu)
    bonus = base_atk * 0.10
    assert get_effective_stat(tengjiao, StatType.atk) == approx(base_atk + bonus)
    assert get_effective_stat(flora, StatType.atk) == approx(flora.base_stats.atk + bonus)


def test_maoxuewang_burns_floor_and_clears_huoli():
    engine = make_engine(_team())
    tengjiao = by_template(engine, P1, "tengjiao")
    advance_to(engine, tengjiao)
    _set_huoli(tengjiao, 25)
    _force_free_dish(engine, tengjiao, DISH_MAOXUEWANG)
    assert _submit_serve(engine, tengjiao, tengjiao.unique_id)
    assert _huoli_stacks(tengjiao) == 0
    enemy = engine.get_active_spirits("p2")[0]
    burns = effects_of(enemy, EffectType.debuff_burn)
    assert burns and burns[0].stacks == 8
    assert any(e.display_name == "毛血旺" for e in enemy.effects)


def test_crossing_two_thresholds_queues_two():
    engine = make_engine(_team())
    tengjiao = by_template(engine, P1, "tengjiao")
    advance_to(engine, tengjiao)
    from roco.core.spirits.tengjiao import tengjiao_logic

    tengjiao_logic._add_huoli(engine, tengjiao, 25)  # 0 -> 25 crosses 10 and 20
    assert _pending_free(tengjiao) == [DISH_LAZIJI, DISH_SHUIZHUYU]
    assert len(engine.state.extra_action_queue) == 2


def test_preview_dish_commits_without_spending_turn():
    from roco.core.spirits.tengjiao import COMMITTED_DISH_KEY, tengjiao_logic

    engine = make_engine(_team())
    tengjiao = by_template(engine, P1, "tengjiao")
    advance_to(engine, tengjiao)
    before_actions = engine.state.action_count
    energy_before = engine.state.players[P1].team_energy
    ok = engine.submit_action(
        P1,
        {
            "type": ActionType.use_skill.value,
            "playerId": P1,
            "actorId": tengjiao.unique_id,
            "skillId": "tengjiao_skill3",
            "previewDish": True,
        },
    )
    assert ok
    dish = tengjiao.sync_attrs.get(COMMITTED_DISH_KEY)
    assert dish in (DISH_LAZIJI, DISH_SHUIZHUYU, DISH_MAOXUEWANG)
    assert tengjiao_logic.peek_serve_dish(engine, tengjiao) == dish
    assert engine.state.action_count == before_actions
    assert engine.state.players[P1].team_energy == energy_before
    assert engine.state.phase == BattlePhase.waiting_for_action
    assert engine.state.active_actor_id == tengjiao.unique_id


def test_serve_target_type_depends_on_dish():
    from roco.core.battle.types import TargetType
    from roco.core.spirits import get_spirit_template
    from roco.core.spirits.tengjiao import tengjiao_logic

    engine = make_engine(_team())
    tengjiao = by_template(engine, P1, "tengjiao")
    advance_to(engine, tengjiao)
    skill = next(s for s in get_spirit_template("tengjiao").skills if s.id == "tengjiao_skill3")
    assert skill.target_type == TargetType.none
    assert tengjiao_logic.get_skill_target_type(engine, tengjiao, skill) == TargetType.none

    _force_free_dish(engine, tengjiao, DISH_LAZIJI)
    assert (
        tengjiao_logic.get_skill_target_type(engine, tengjiao, skill)
        == TargetType.single_ally
    )
    engine.state.extra_action_queue.clear()
    _set_pending_free(tengjiao, [])
    _force_free_dish(engine, tengjiao, DISH_SHUIZHUYU)
    assert tengjiao_logic.get_skill_target_type(engine, tengjiao, skill) == TargetType.self
    engine.state.extra_action_queue.clear()
    _set_pending_free(tengjiao, [])
    _force_free_dish(engine, tengjiao, DISH_MAOXUEWANG)
    assert (
        tengjiao_logic.get_skill_target_type(engine, tengjiao, skill)
        == TargetType.all_enemies
    )
