from __future__ import annotations

from roco.core.battle.damage import calculate_damage
from roco.core.battle.dot import trigger_burn_damage, trigger_tianhuo_damage
from roco.core.battle.effect_meta import stack_count
from roco.core.battle.effects import (
    apply_burn_stacks,
    apply_fanji,
    apply_parasite_stacks,
    apply_poison_stacks,
    get_fanji_effect,
    get_tianhuo_effect,
    purge_debuffs,
)
from roco.core.battle.types import BattleLogType, DamageType, EffectType, StatType
from roco.core.battle.utils import get_effective_stat, make_effect
from roco.core.spirits import get_spirit_logic, get_spirit_template
from roco.core.spirits.nanluzhuque import (
    DEBUFF_TIANHUO_CHANCE,
    grant_tianhuo,
)
from roco.net.serialize import state_from_dict, state_to_dict
from tests.conftest import P1, P2, by_template, cast_skill


P1_TEAM = ("nanluzhuque", "flora", "clawdragon", "chaosling", "starweaver")
P2_TEAM = ("qiuka", "fanying", "tita", "guifashi", "flora")


def make_zhuque_battle(engine_factory):
    engine = engine_factory(P1_TEAM, P2_TEAM)
    return engine, by_template(engine, P1, "nanluzhuque")


def test_template_and_skill_values_are_registered() -> None:
    template = get_spirit_template("nanluzhuque")
    assert template is not None
    assert template.name == "南陆朱雀"
    assert template.base_stats.attack == 140
    assert template.elements == (DamageType.fire,)
    assert [skill.energy_cost for skill in template.skills] == [4, 4]
    assert get_spirit_logic(template.id) is not None
    assert DEBUFF_TIANHUO_CHANCE == 0.75


def test_tianhuo_damage_uses_12_percent_points_per_stack_and_halves(
    engine_factory,
) -> None:
    engine, zhuque = make_zhuque_battle(engine_factory)
    target = engine.get_active_spirits(P2)[0]
    assert grant_tianhuo(engine, zhuque, target, 10)
    expected = calculate_damage(
        zhuque.base_stats.attack * (0.20 + 0.012 * 10),
        DamageType.fire,
        zhuque,
        target,
        sustained="tianhuo",
    )
    before = target.current_hp

    trigger_tianhuo_damage(engine, target)

    assert before - target.current_hp == expected
    assert stack_count(get_tianhuo_effect(target, zhuque.unique_id)) == 5


def test_tianhuo_damage_counts_at_most_100_but_halves_actual_stacks(
    engine_factory,
) -> None:
    engine, zhuque = make_zhuque_battle(engine_factory)
    target = engine.get_active_spirits(P2)[0]
    target.max_hp = target.current_hp = 10_000
    assert grant_tianhuo(engine, zhuque, target, 120)
    expected = calculate_damage(
        zhuque.base_stats.attack * (0.20 + 0.012 * 100),
        DamageType.fire,
        zhuque,
        target,
        sustained="tianhuo",
    )
    before = target.current_hp

    trigger_tianhuo_damage(engine, target)

    assert before - target.current_hp == expected
    assert stack_count(get_tianhuo_effect(target, zhuque.unique_id)) == 60


def test_ordinary_dot_immediately_triggers_tianhuo(engine_factory) -> None:
    engine, zhuque = make_zhuque_battle(engine_factory)
    target = engine.get_active_spirits(P2)[0]
    burner = engine.get_active_spirits(P1)[1]
    assert apply_burn_stacks(target, burner.unique_id, 1)
    assert grant_tianhuo(engine, zhuque, target, 20)

    trigger_burn_damage(engine, target)

    assert stack_count(get_tianhuo_effect(target, zhuque.unique_id)) == 10
    assert any("天火" in entry.message for entry in engine.state.battle_log)


def test_fanji_amplifies_attribute_but_not_fixed_damage(engine_factory) -> None:
    engine, zhuque = make_zhuque_battle(engine_factory)
    target = engine.get_active_spirits(P2)[0]
    raw = 100.0
    normal_base = calculate_damage(raw, DamageType.fire, zhuque, target)
    dot_base = calculate_damage(
        raw, DamageType.fire, zhuque, target, sustained="tianhuo"
    )
    fixed_base = calculate_damage(raw, DamageType.fixed, zhuque, target)
    assert apply_fanji(target, zhuque.unique_id)

    assert calculate_damage(raw, DamageType.fire, zhuque, target) == int(
        normal_base * 1.10
    )
    assert calculate_damage(
        raw, DamageType.fire, zhuque, target, sustained="tianhuo"
    ) == int(dot_base * 1.30)
    assert calculate_damage(raw, DamageType.fixed, zhuque, target) == fixed_base


def test_fanji_protects_sustained_effects_from_same_cleanse(engine_factory) -> None:
    engine, zhuque = make_zhuque_battle(engine_factory)
    target = engine.get_active_spirits(P2)[0]
    assert apply_fanji(target, zhuque.unique_id)
    assert apply_burn_stacks(target, zhuque.unique_id, 2)
    assert apply_poison_stacks(target, zhuque.unique_id, 2)
    assert apply_parasite_stacks(target, zhuque.unique_id, 2)
    assert grant_tianhuo(engine, zhuque, target, 2)
    target.effects.append(
        make_effect(EffectType.debuff_stun, zhuque.unique_id, duration_turns=1)
    )

    removed = purge_debuffs(target)

    assert {effect.type for effect in removed} == {
        EffectType.debuff_fanji,
        EffectType.debuff_stun,
    }
    remaining = {effect.type for effect in target.effects}
    assert EffectType.debuff_burn in remaining
    assert EffectType.debuff_poison in remaining
    assert EffectType.debuff_parasite in remaining
    assert EffectType.debuff_tianhuo in remaining


def test_fanji_skill_applies_three_turns_and_15_tianhuo(
    engine_factory, monkeypatch
) -> None:
    engine, zhuque = make_zhuque_battle(engine_factory)
    logic = get_spirit_logic(zhuque.template_id)
    assert logic is not None
    original_next_rng = engine.next_rng

    class MissRng:
        def random(self):
            return 0.99

    monkeypatch.setattr(
        engine,
        "next_rng",
        lambda domain, *parts: (
            MissRng()
            if domain == "nanluzhuque_qunhuofuchen"
            else original_next_rng(domain, *parts)
        ),
    )

    logic.execute_skill(
        engine,
        P1,
        zhuque,
        {"skillId": "nanluzhuque_skill1", "actorId": zhuque.unique_id},
    )

    for target in engine.get_active_spirits(P2):
        fanji = get_fanji_effect(target, zhuque.unique_id)
        assert fanji is not None and fanji.duration_turns == 3
        assert stack_count(get_tianhuo_effect(target, zhuque.unique_id)) == 15


def test_fanji_submits_through_normal_action_flow_and_spends_energy(
    engine_factory,
) -> None:
    engine, zhuque = make_zhuque_battle(engine_factory)
    engine.state.players[P1].team_energy = 10

    assert cast_skill(engine, zhuque, "nanluzhuque_skill1")

    assert engine.state.players[P1].team_energy == 6
    assert all(
        get_fanji_effect(target, zhuque.unique_id) is not None
        for target in engine.get_active_spirits(P2)
    )


def test_fenjie_applies_neighbors_and_triggers_tianhuo(engine_factory) -> None:
    engine, zhuque = make_zhuque_battle(engine_factory)
    targets = engine.get_active_spirits(P2)
    primary = sorted(targets, key=lambda spirit: spirit.slot)[2]
    neighbors = engine.get_adjacent_enemies(primary)
    logic = get_spirit_logic(zhuque.template_id)
    assert logic is not None

    logic.execute_skill(
        engine,
        P1,
        zhuque,
        {
            "skillId": "nanluzhuque_skill2",
            "actorId": zhuque.unique_id,
            "targetId": primary.unique_id,
        },
    )

    assert stack_count(get_tianhuo_effect(primary, zhuque.unique_id)) == 15
    for neighbor in neighbors:
        assert stack_count(get_tianhuo_effect(neighbor, zhuque.unique_id)) == 7
    untouched = [
        target
        for target in targets
        if target.unique_id not in {primary.unique_id, *(n.unique_id for n in neighbors)}
    ]
    assert all(get_tianhuo_effect(target, zhuque.unique_id) is None for target in untouched)


def test_negative_effect_hook_can_add_tianhuo_under_fanji(
    engine_factory, monkeypatch
) -> None:
    import roco.core.spirits.nanluzhuque as module

    engine, zhuque = make_zhuque_battle(engine_factory)
    target = engine.get_active_spirits(P2)[0]
    assert apply_fanji(target, zhuque.unique_id)
    draws = iter((0.1, 0.9))

    class StubRng:
        def random(self):
            return next(draws)

    monkeypatch.setattr(engine, "next_rng", lambda *args: StubRng())
    stun = make_effect(EffectType.debuff_stun, zhuque.unique_id, duration_turns=1)
    target.effects.append(stun)

    engine.add_log(
        BattleLogType.effect_applied,
        "test debuff",
        {
            "targetId": target.unique_id,
            "sourceId": zhuque.unique_id,
            "effectId": stun.id,
            "effectType": stun.type.value,
        },
    )

    assert stack_count(get_tianhuo_effect(target, zhuque.unique_id)) == 1


def test_applying_tianhuo_itself_can_trigger_qunhuofuchen(
    engine_factory, monkeypatch
) -> None:
    engine, zhuque = make_zhuque_battle(engine_factory)
    target = engine.get_active_spirits(P2)[0]
    assert apply_fanji(target, zhuque.unique_id)
    draws = iter((0.1, 0.9))

    class StubRng:
        def random(self):
            return next(draws)

    monkeypatch.setattr(engine, "next_rng", lambda *args: StubRng())

    assert grant_tianhuo(engine, zhuque, target, 15)

    assert stack_count(get_tianhuo_effect(target, zhuque.unique_id)) == 16


def test_first_fanji_does_not_trigger_but_refresh_does(
    engine_factory, monkeypatch
) -> None:
    engine, zhuque = make_zhuque_battle(engine_factory)
    target = engine.get_active_spirits(P2)[0]
    draws = iter((0.1, 0.9))

    class StubRng:
        def random(self):
            return next(draws)

    original_next_rng = engine.next_rng
    monkeypatch.setattr(
        engine,
        "next_rng",
        lambda domain, *parts: (
            StubRng()
            if domain == "nanluzhuque_qunhuofuchen"
            else original_next_rng(domain, *parts)
        ),
    )
    prior_effect_types = [effect.type.value for effect in target.effects]
    assert apply_fanji(target, zhuque.unique_id)
    fanji = get_fanji_effect(target, zhuque.unique_id)
    assert fanji is not None

    engine.add_log(
        BattleLogType.effect_applied,
        "fanji applied",
        {
            "targetId": target.unique_id,
            "sourceId": zhuque.unique_id,
            "effectId": fanji.id,
            "effectType": fanji.type.value,
            "priorEffectTypes": prior_effect_types,
        },
    )
    assert get_tianhuo_effect(target, zhuque.unique_id) is None

    prior_effect_types = [effect.type.value for effect in target.effects]
    assert apply_fanji(target, zhuque.unique_id)
    engine.add_log(
        BattleLogType.effect_applied,
        "fanji refreshed",
        {
            "targetId": target.unique_id,
            "sourceId": zhuque.unique_id,
            "effectId": fanji.id,
            "effectType": fanji.type.value,
            "priorEffectTypes": prior_effect_types,
        },
    )

    assert stack_count(get_tianhuo_effect(target, zhuque.unique_id)) == 1


def test_nanluzhuque_effects_survive_state_roundtrip(engine_factory) -> None:
    engine, zhuque = make_zhuque_battle(engine_factory)
    target = engine.get_active_spirits(P2)[0]
    assert apply_fanji(target, zhuque.unique_id)
    assert grant_tianhuo(engine, zhuque, target, 23)
    stacks_before = stack_count(get_tianhuo_effect(target, zhuque.unique_id))

    restored = state_from_dict(state_to_dict(engine.state))
    restored_target = next(
        spirit
        for spirit in restored.players[P2].spirits
        if spirit.unique_id == target.unique_id
    )

    fanji = get_fanji_effect(restored_target, zhuque.unique_id)
    assert fanji is not None and fanji.duration_turns == 3
    assert (
        stack_count(get_tianhuo_effect(restored_target, zhuque.unique_id))
        == stacks_before
    )
