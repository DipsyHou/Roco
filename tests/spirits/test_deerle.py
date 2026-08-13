"""梅花德尔勒 — 看破 / 剑花 / 穿刺 / 敏锐。"""

from __future__ import annotations

from tests.conftest import P1, P2, by_template, cast_skill, normal_attack
from roco.core.battle.types import DamageType, EffectType, StatType
from roco.core.battle.utils import make_effect, calculate_damage, get_effective_stat
from roco.core.spirits.deerle import (
    LOUDONG_DAMAGE_BOOST,
    LOUDONG_HIT_TAG,
    NORMAL_ATK_RATIO,
    deerle_logic,
)


def _clear_flaws(engine, player_id: str) -> None:
    for spirit in engine.get_all_spirits(player_id):
        spirit.effects = [e for e in spirit.effects if e.type != EffectType.debuff_flaw]


def test_opening_jianwu_and_two_flaws(engine_factory):
    engine = engine_factory(
        ("deerle", "flora", "tita", "fanying", "clawdragon"),
        ("steamdragon", "chaosling", "qiuka", "starweaver", "huxian"),
    )
    deerle = by_template(engine, P1, "deerle")
    jianwu = next(e for e in deerle.effects if e.type == EffectType.state_jianwu)
    assert jianwu.stacks == 1
    assert jianwu.duration_turns == 5

    flaw_count = sum(
        1
        for s in engine.get_all_spirits(P2)
        for e in s.effects
        if e.type == EffectType.debuff_flaw
    )
    assert flaw_count == 2


def test_normal_attack_spreads_flaw_and_stacks_jianwu(engine_factory):
    engine = engine_factory(
        ("deerle", "flora", "tita", "fanying", "clawdragon"),
        ("steamdragon", "chaosling", "qiuka", "starweaver", "huxian"),
    )
    deerle = by_template(engine, P1, "deerle")
    enemy = by_template(engine, P2, "steamdragon")
    _clear_flaws(engine, P2)
    deerle_logic._apply_flaw(engine, deerle, enemy)

    assert normal_attack(engine, deerle, enemy)

    assert sum(1 for e in enemy.effects if e.type == EffectType.debuff_flaw) == 0
    spread = sum(
        1
        for s in engine.get_all_spirits(P2)
        if s.unique_id != enemy.unique_id
        for e in s.effects
        if e.type == EffectType.debuff_flaw
    )
    assert spread == 2
    assert next(e.stacks for e in deerle.effects if e.type == EffectType.state_jianwu) == 2


def test_normal_attack_does_not_recreate_expired_jianwu(engine_factory):
    engine = engine_factory(
        ("deerle", "flora", "tita", "fanying", "clawdragon"),
        ("steamdragon", "chaosling", "qiuka", "starweaver", "huxian"),
    )
    deerle = by_template(engine, P1, "deerle")
    enemy = by_template(engine, P2, "steamdragon")
    deerle.effects = [e for e in deerle.effects if e.type != EffectType.state_jianwu]

    assert normal_attack(engine, deerle, enemy)
    assert _get_jianwu(deerle) is None


def _get_jianwu(spirit):
    return next((e for e in spirit.effects if e.type == EffectType.state_jianwu), None)


def test_loudong_requires_applier_and_uses_damage_boost(engine_factory):
    engine = engine_factory(
        ("deerle", "flora", "tita", "fanying", "clawdragon"),
        ("steamdragon", "chaosling", "qiuka", "starweaver", "huxian"),
    )
    deerle = by_template(engine, P1, "deerle")
    enemy = by_template(engine, P2, "steamdragon")
    _clear_flaws(engine, P2)
    for e in list(enemy.effects):
        if e.type == EffectType.state_loudong_baichu:
            enemy.effects.remove(e)

    # 非本人施加的漏洞：不触发
    enemy.effects.append(
        make_effect(EffectType.state_loudong_baichu, "someone-else", display_name="漏洞百出")
    )
    hp_before = enemy.current_hp
    expected_plain = calculate_damage(
        get_effective_stat(deerle, StatType.atk) * NORMAL_ATK_RATIO,
        DamageType.physical,
        deerle,
        enemy,
    )
    assert normal_attack(engine, deerle, enemy)
    assert any(e.type == EffectType.state_loudong_baichu for e in enemy.effects)
    assert hp_before - enemy.current_hp == expected_plain
    assert engine.state.extra_action_queue == []
    assert not any(e.effect_tag == LOUDONG_HIT_TAG for e in deerle.effects)

    # 本人施加：伤害走 +20% 造成伤害加成，并解除 + 额外行动
    enemy.effects = [e for e in enemy.effects if e.type != EffectType.state_loudong_baichu]
    enemy.effects.append(
        make_effect(
            EffectType.state_loudong_baichu,
            deerle.unique_id,
            display_name="漏洞百出",
        )
    )
    # 临时加成与结算同管线的期望值
    boost = make_effect(
        EffectType.buff_damage_percent_boost,
        deerle.unique_id,
        value=LOUDONG_DAMAGE_BOOST,
        damage_type=DamageType.physical,
        effect_tag=LOUDONG_HIT_TAG,
    )
    deerle.effects.append(boost)
    expected_boosted = calculate_damage(
        get_effective_stat(deerle, StatType.atk) * NORMAL_ATK_RATIO,
        DamageType.physical,
        deerle,
        enemy,
    )
    deerle.effects.remove(boost)

    hp_before = enemy.current_hp
    assert normal_attack(engine, deerle, enemy)
    assert hp_before - enemy.current_hp == expected_boosted
    assert not any(e.type == EffectType.state_loudong_baichu for e in enemy.effects)
    assert not any(e.effect_tag == LOUDONG_HIT_TAG for e in deerle.effects)
    assert len(engine.state.extra_action_queue) == 1
    assert engine.state.extra_action_queue[0].source == "loudong_baichu"


def test_keen_marks_loudong_at_three_flaws(engine_factory):
    engine = engine_factory(
        ("deerle", "flora", "tita", "fanying", "clawdragon"),
        ("steamdragon", "chaosling", "qiuka", "starweaver", "huxian"),
    )
    deerle = by_template(engine, P1, "deerle")
    enemy = by_template(engine, P2, "steamdragon")
    _clear_flaws(engine, P2)
    for _ in range(3):
        deerle_logic._apply_flaw(engine, deerle, enemy)

    assert cast_skill(engine, deerle, "deerle_skill3")
    assert any(
        e.type == EffectType.state_loudong_baichu and e.source_id == deerle.unique_id
        for e in enemy.effects
    )


def test_stab_applies_flaw_before_damage(engine_factory):
    engine = engine_factory(
        ("deerle", "flora", "tita", "fanying", "clawdragon"),
        ("steamdragon", "chaosling", "qiuka", "starweaver", "huxian"),
    )
    deerle = by_template(engine, P1, "deerle")
    enemy = by_template(engine, P2, "steamdragon")
    _clear_flaws(engine, P2)

    assert cast_skill(engine, deerle, "deerle_skill2", enemy)
    assert sum(1 for e in enemy.effects if e.type == EffectType.debuff_flaw) >= 1


def test_jianhua_recreates_jianwu_after_expiry(engine_factory):
    engine = engine_factory(
        ("deerle", "flora", "tita", "fanying", "clawdragon"),
        ("steamdragon", "chaosling", "qiuka", "starweaver", "huxian"),
    )
    deerle = by_template(engine, P1, "deerle")
    deerle.effects = [e for e in deerle.effects if e.type != EffectType.state_jianwu]

    deerle_logic._skill_jianhua(engine, P1, deerle, {})
    jianwu = _get_jianwu(deerle)
    assert jianwu is not None
    assert jianwu.stacks == 1
    assert jianwu.duration_turns == 5
