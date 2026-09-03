from __future__ import annotations

from roco.core.battle.damage_modifiers import SUSTAINED_DAMAGE_TAG
from roco.core.battle.dot import (
    process_parasite_on_action_end,
    trigger_parasite_damage,
)
from roco.core.battle.events import DamageSource
from roco.core.battle.utils import (
    apply_parasite_stacks,
    calculate_damage,
    get_parasite_effects,
    make_effect,
)
from roco.core.battle.types import DamageType, EffectType
from roco.core.spirits._combat import deal_atk_ratio
from tests.conftest import by_template, cast_skill, make_engine, P1, P2


def test_parasite_stacks_per_source():
    engine = make_engine(
        ("gulum", "flora", "clawdragon", "chaosling", "starweaver"),
        ("qiuka", "fanying", "tita", "guifashi", "flora"),
    )
    gulum = by_template(engine, P1, "gulum")
    ally = by_template(engine, P1, "flora")
    target = by_template(engine, P2, "qiuka")

    apply_parasite_stacks(target, gulum.unique_id, 2)
    apply_parasite_stacks(target, ally.unique_id, 3)

    effects = get_parasite_effects(target)
    assert len(effects) == 2
    stacks = sorted(effect.stacks for effect in effects)
    assert stacks == [2, 3]


def test_parasite_ignores_general_percent_boost():
    engine = make_engine()
    attacker = by_template(engine, P1, "flora")
    defender = by_template(engine, P2, "qiuka")
    defender.base_stats.mag_def = 100
    attacker.base_stats.mag_atk = 200
    attacker.effects.append(
        make_effect(
            EffectType.buff_damage_percent_boost,
            attacker.unique_id,
            duration_turns=1,
            value=0.5,
        )
    )
    apply_parasite_stacks(defender, attacker.unique_id, 5)

    plain = calculate_damage(40, DamageType.magical, attacker, defender, sustained="parasite")
    boosted = calculate_damage(40, DamageType.magical, attacker, defender)
    assert plain == 40
    assert boosted == 60


def test_parasite_applies_sustained_taken_amp():
    engine = make_engine()
    attacker = by_template(engine, P1, "flora")
    defender = by_template(engine, P2, "qiuka")
    defender.base_stats.mag_def = 100
    attacker.base_stats.mag_atk = 200
    defender.effects.append(
        make_effect(
            EffectType.debuff_taken_damage_percent_boost,
            attacker.unique_id,
            duration_turns=3,
            value=0.15,
            display_name="毛血旺",
            effect_tag=SUSTAINED_DAMAGE_TAG,
        )
    )

    base = calculate_damage(40, DamageType.magical, attacker, defender, sustained="parasite")
    assert base == 46


def test_trigger_parasite_does_not_reduce_stacks():
    engine = make_engine(
        ("gulum", "flora", "clawdragon", "chaosling", "starweaver"),
        ("qiuka", "fanying", "tita", "guifashi", "flora"),
    )
    gulum = by_template(engine, P1, "gulum")
    target = by_template(engine, P2, "qiuka")
    gulum.base_stats.mag_atk = 100
    apply_parasite_stacks(target, gulum.unique_id, 4)

    trigger_parasite_damage(engine, target)
    assert get_parasite_effects(target)[0].stacks == 4


def test_parasite_action_end_reduces_stacks():
    engine = make_engine(
        ("gulum", "flora", "clawdragon", "chaosling", "starweaver"),
        ("qiuka", "fanying", "tita", "guifashi", "flora"),
    )
    gulum = by_template(engine, P1, "gulum")
    target = by_template(engine, P2, "qiuka")
    gulum.base_stats.mag_atk = 100
    apply_parasite_stacks(target, gulum.unique_id, 2)

    process_parasite_on_action_end(engine, target)
    assert get_parasite_effects(target)[0].stacks == 1


def test_gulum_seed_grants_parasite():
    engine = make_engine(
        ("gulum", "flora", "clawdragon", "chaosling", "starweaver"),
        ("qiuka", "fanying", "tita", "guifashi", "flora"),
    )
    gulum = by_template(engine, P1, "gulum")
    target = by_template(engine, P2, "qiuka")
    gulum.energy = 10

    cast_skill(engine, gulum, "gulum_skill1", target=target)

    effects = get_parasite_effects(target)
    assert len(effects) == 1
    assert effects[0].stacks == 4
    assert effects[0].source_id == gulum.unique_id


def test_gulum_nutrient_heals_ally_when_healthy():
    engine = make_engine(
        ("gulum", "flora", "clawdragon", "chaosling", "starweaver"),
        ("qiuka", "fanying", "tita", "guifashi", "flora"),
    )
    gulum = by_template(engine, P1, "gulum")
    ally = by_template(engine, P1, "flora")
    enemy = by_template(engine, P2, "qiuka")
    gulum.current_hp = 800
    gulum.max_hp = 1000
    ally_hp_before = 500
    ally.current_hp = ally_hp_before
    ally.max_hp = 1000
    enemy.base_stats.atk = 200
    ally.base_stats.def_ = 100

    deal_atk_ratio(
        engine,
        enemy,
        ally,
        1.0,
        lambda actual: f"hit {actual}",
        source=DamageSource.skill,
    )

    expected_heal = int(gulum.max_hp * 0.02)
    assert ally.current_hp == ally_hp_before - 200 + expected_heal


def test_gulum_nutrient_heals_self_when_healthy_and_takes_damage():
    engine = make_engine(
        ("gulum", "flora", "clawdragon", "chaosling", "starweaver"),
        ("qiuka", "fanying", "tita", "guifashi", "flora"),
    )
    gulum = by_template(engine, P1, "gulum")
    enemy = by_template(engine, P2, "qiuka")
    gulum.current_hp = 800
    gulum.max_hp = 1000
    enemy.base_stats.atk = 200
    gulum.base_stats.def_ = 100
    hp_before = gulum.current_hp

    deal_atk_ratio(
        engine,
        enemy,
        gulum,
        1.0,
        lambda actual: f"hit {actual}",
        source=DamageSource.skill,
    )

    expected_heal = int(gulum.max_hp * 0.02)
    assert gulum.current_hp == hp_before - 200 + expected_heal
