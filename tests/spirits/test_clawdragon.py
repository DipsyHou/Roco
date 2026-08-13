from __future__ import annotations

from tests.conftest import P1, P2, by_template, cast_skill, effects_of
from roco.core.battle.events import DamageSource
from roco.core.battle.types import EffectType, StatType
from roco.core.battle.utils import get_effective_stat
from roco.core.spirits import get_spirit_logic


def test_dragon_dance_boosts_atk_and_speed(engine_factory):
    engine = engine_factory(("clawdragon", "flora", "chaosling", "starweaver", "steamdragon"))
    claw = by_template(engine, P1, "clawdragon")
    base_atk = get_effective_stat(claw, StatType.atk)
    base_speed = get_effective_stat(claw, StatType.speed)

    assert cast_skill(engine, claw, "clawdragon_skill2")

    assert get_effective_stat(claw, StatType.atk) == base_atk * 1.2
    assert get_effective_stat(claw, StatType.speed) == base_speed * 1.2


def test_shoulder_throw_applies_stun(engine_factory):
    engine = engine_factory(("clawdragon", "flora", "chaosling", "starweaver", "steamdragon"))
    claw = by_template(engine, P1, "clawdragon")
    enemy = engine.get_active_spirits(P2)[0]

    assert cast_skill(engine, claw, "clawdragon_skill3", target_id=enemy.unique_id)

    stun = effects_of(enemy, EffectType.debuff_stun)[0]
    assert stun.duration_turns == 1


def test_legendary_power_uses_current_hp(engine_factory):
    engine = engine_factory(("clawdragon", "flora", "chaosling", "starweaver", "steamdragon"))
    claw = by_template(engine, P1, "clawdragon")
    enemy = engine.get_active_spirits(P2)[0]
    enemy.current_hp = 400

    hp_before = enemy.current_hp
    assert cast_skill(engine, claw, "clawdragon_skill1", target_id=enemy.unique_id)
    assert enemy.current_hp < hp_before


def test_guardian_passive_triggers_once_until_turn_start(engine_factory):
    engine = engine_factory(("clawdragon", "flora", "chaosling", "starweaver", "steamdragon"))
    claw = by_template(engine, P1, "clawdragon")
    attacker = engine.get_active_spirits(P2)[0]
    logic = get_spirit_logic("clawdragon")

    claw._guardian_passive_used = False
    engine.notify_damage_taken(attacker, claw, 30, source=DamageSource.attack)
    engine.notify_damage_taken(attacker, claw, 30, source=DamageSource.attack)

    guardian_buffs = [
        e for e in claw.effects
        if e.type == EffectType.buff_stat_percent_boost and e.display_name == "守护者"
    ]
    assert len(guardian_buffs) == 2

    logic.on_turn_start(engine, claw)
    claw._guardian_passive_used = False
    engine.notify_damage_taken(attacker, claw, 20, source=DamageSource.attack)

    guardian_buffs = [
        e for e in claw.effects
        if e.type == EffectType.buff_stat_percent_boost and e.display_name == "守护者"
    ]
    assert len(guardian_buffs) == 4
