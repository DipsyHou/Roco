from __future__ import annotations

from tests.conftest import P1, P2, by_template, cast_skill, effects_of
from roco.core.battle.effects import make_effect
from roco.core.battle.events import DamageSource
from roco.core.battle.utils import apply_damage
from roco.core.battle.types import EffectType, StatType


def test_heal_self_purges_one_debuff(engine_factory):
    engine = engine_factory(("flora", "clawdragon", "chaosling", "starweaver", "steamdragon"))
    flora = by_template(engine, P1, "flora")
    flora.current_hp -= 100
    flora.effects.append(
        make_effect(
            EffectType.debuff_stat_percent_reduction,
            "x",
            duration_turns=3,
            stat_type=StatType.speed,
            value=0.1,
        )
    )

    assert cast_skill(engine, flora, "flora_skill1", flora)

    assert flora.current_hp > flora.max_hp - 100
    assert not effects_of(flora, EffectType.debuff_stat_percent_reduction)


def test_pain_relief_grants_duration_mitigation(engine_factory):
    engine = engine_factory(("flora", "clawdragon", "chaosling", "starweaver", "steamdragon"))
    flora = by_template(engine, P1, "flora")

    assert cast_skill(engine, flora, "flora_skill2", flora)

    relief = effects_of(flora, EffectType.buff_taken_damage_percent_reduction)[0]
    assert relief.duration_turns == 1
    assert relief.value == 0.20


def test_anesthesia_dispatches_damage_for_ally_hooks(engine_factory):
    engine = engine_factory(("flora", "starweaver", "clawdragon", "chaosling", "steamdragon"))
    flora = by_template(engine, P1, "flora")
    star = by_template(engine, P1, "starweaver")

    assert cast_skill(engine, flora, "flora_skill3")

    assert star.energy == 3
    assert sum(1 for e in engine.state.battle_log if "共振" in e.message) == 1


def test_anesthesia_damages_all_enemies_and_slows_them(engine_factory):
    engine = engine_factory(("flora", "clawdragon", "chaosling", "starweaver", "steamdragon"))
    flora = by_template(engine, P1, "flora")
    enemies = engine.get_active_spirits(P2)
    hp_before = {enemy.unique_id: enemy.current_hp for enemy in enemies}

    assert cast_skill(engine, flora, "flora_skill3")

    for enemy in enemies:
        assert enemy.current_hp < hp_before[enemy.unique_id]
        slow = effects_of(enemy, EffectType.debuff_stat_percent_reduction)[0]
        assert slow.stat_type == StatType.speed
        assert slow.duration_turns == 2


def test_emergency_support_triggers_after_damage_segment(engine_factory):
    engine = engine_factory(("flora", "clawdragon", "chaosling", "starweaver", "steamdragon"))
    flora = by_template(engine, P1, "flora")
    ally = by_template(engine, P1, "clawdragon")
    enemy = engine.get_active_spirits(P2)[0]
    ally.current_hp = int(ally.max_hp * 0.35)
    actual = apply_damage(ally, int(ally.max_hp * 0.1), ctx=engine)

    engine.notify_damage_taken(enemy, ally, actual, source=DamageSource.attack)

    assert flora.passive_triggered
    assert ally.current_hp > int(ally.max_hp * 0.25)
    assert effects_of(ally, EffectType.buff_stat_percent_boost)


def test_emergency_support_triggers_when_segment_crosses_threshold(engine_factory):
    engine = engine_factory(("flora", "clawdragon", "chaosling", "starweaver", "steamdragon"))
    flora = by_template(engine, P1, "flora")
    ally = by_template(engine, P1, "clawdragon")
    enemy = engine.get_active_spirits(P2)[0]
    ally.current_hp = int(ally.max_hp * 0.5)
    actual = apply_damage(ally, int(ally.max_hp * 0.25), ctx=engine)

    engine.notify_damage_taken(enemy, ally, actual, source=DamageSource.skill)

    assert flora.passive_triggered
    assert ally.current_hp > int(ally.max_hp * 0.25)


def test_emergency_support_once_per_battle(engine_factory):
    engine = engine_factory(("flora", "clawdragon", "chaosling", "starweaver", "steamdragon"))
    flora = by_template(engine, P1, "flora")
    ally = by_template(engine, P1, "clawdragon")
    enemy = engine.get_active_spirits(P2)[0]
    ally.current_hp = int(ally.max_hp * 0.2)
    actual1 = apply_damage(ally, 1, ctx=engine)
    engine.notify_damage_taken(enemy, ally, actual1, source=DamageSource.attack)
    hp_after_first = ally.current_hp
    actual2 = apply_damage(ally, 50, ctx=engine)
    engine.notify_damage_taken(enemy, ally, actual2, source=DamageSource.attack)

    assert flora.passive_triggered
    assert ally.current_hp == hp_after_first - actual2
