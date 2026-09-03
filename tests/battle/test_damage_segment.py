from __future__ import annotations

from roco.core.battle.damage_segment import execute_damage_segment, resolve_damage_applications
from roco.core.battle.events import DamageSource
from roco.core.battle.utils import calculate_damage, make_effect
from roco.core.battle.types import DamageType, EffectType
from tests.conftest import by_template, make_engine, P1, P2


def test_deep_root_splits_damage_evenly():
    engine = make_engine(
        ("gulum", "flora", "clawdragon", "chaosling", "starweaver"),
        ("qiuka", "fanying", "tita", "guifashi", "flora"),
    )
    gulum = by_template(engine, P1, "gulum")
    ally = by_template(engine, P1, "flora")
    gulum.effects.append(
        make_effect(
            EffectType.state_shengen,
            gulum.unique_id,
            duration_turns=3,
            display_name="深根",
        )
    )
    ally.current_hp = 1000
    gulum.current_hp = 1000

    apps = resolve_damage_applications(engine, ally, 101)
    amounts = {app.target.unique_id: app.segment_amount for app in apps}
    emit_flags = {app.target.unique_id: app.emit_damage_event for app in apps}

    assert amounts[ally.unique_id] == 61
    assert amounts[gulum.unique_id] == 40
    assert emit_flags[ally.unique_id] is True
    assert emit_flags[gulum.unique_id] is False


def test_lifesteal_uses_pre_shield_segment():
    engine = make_engine(
        ("xiaozong", "flora", "clawdragon", "chaosling", "starweaver"),
        ("qiuka", "fanying", "tita", "guifashi", "flora"),
    )
    actor = by_template(engine, P1, "xiaozong")
    defender = by_template(engine, P2, "qiuka")
    actor.base_stats.mag_atk = 200
    defender.base_stats.mag_def = 100
    actor.current_hp = 500
    actor.max_hp = 1000
    defender.effects.append(
        make_effect(
            EffectType.state_shield,
            "shield-src",
            value=500,
            display_name="测试盾",
        )
    )

    segment = calculate_damage(100, DamageType.magical, actor, defender)
    before_hp = actor.current_hp
    execute_damage_segment(
        engine,
        actor,
        defender,
        segment,
        source=DamageSource.skill,
        lifesteal_ratio=0.30,
        lifesteal_healer=actor,
    )
    assert actor.current_hp - before_hp == int(segment * 0.30)


def test_gulum_share_portion_does_not_emit_damage_event():
    """Shared damage deducts HP but does not re-trigger nutrient on the sharer."""
    engine = make_engine(
        ("gulum", "flora", "clawdragon", "chaosling", "starweaver"),
        ("qiuka", "fanying", "tita", "guifashi", "flora"),
    )
    gulum = by_template(engine, P1, "gulum")
    ally = by_template(engine, P1, "flora")
    gulum.effects.append(
        make_effect(
            EffectType.state_shengen,
            gulum.unique_id,
            duration_turns=3,
            display_name="深根",
        )
    )
    gulum.current_hp = 200
    gulum.max_hp = 1000
    ally.current_hp = 800
    ally.max_hp = 1000
    gulum_hp_before = gulum.current_hp

    execute_damage_segment(
        engine,
        by_template(engine, P2, "qiuka"),
        ally,
        100,
        source=DamageSource.skill,
    )

    assert gulum.current_hp == gulum_hp_before - 40 + int(gulum.max_hp * 0.02)
    assert ally.current_hp == 800 - 60
