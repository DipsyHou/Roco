from __future__ import annotations

from tests.conftest import P1, P2, by_template, cast_skill, effects_of, normal_attack, submit
from roco.core.battle.types import ActionType, EffectType, StatType
from roco.core.battle.utils import get_effective_stat


def _tagged(spirit, tag: str):
    return [effect for effect in spirit.effects if effect.effect_tag == tag]


def test_guagua_battle_start_marks_first_ally_and_gets_passive_bonuses(engine_factory):
    engine = engine_factory(("flora", "guagua"), ("qiuka", "fanying"))
    flora = by_template(engine, P1, "flora")
    guagua = by_template(engine, P1, "guagua")

    assert any(effect.type == EffectType.state_shifu for effect in flora.effects)
    assert get_effective_stat(guagua, StatType.atk) == 120 * 1.12
    assert get_effective_stat(guagua, StatType.mag_atk) == 120 * 1.12


def test_teacher_attack_auto_triggers_learned_once_per_guagua_turn(engine_factory):
    engine = engine_factory(("flora", "guagua"), ("qiuka", "fanying"))
    flora = by_template(engine, P1, "flora")
    guagua = by_template(engine, P1, "guagua")
    target = by_template(engine, P2, "qiuka")

    before_hp = target.current_hp
    assert normal_attack(engine, flora, target)

    assert guagua.sync_attrs["guagua_learned_used"] == 1
    assert guagua.sync_attrs["guagua_learned_target_id"] == target.unique_id
    assert engine.current_extra_slot() is not None
    assert engine.current_extra_slot().actor_id == guagua.unique_id
    assert engine.current_extra_slot().source == "guagua_learned"
    assert target.current_hp < before_hp
    after_teacher_attack_hp = target.current_hp

    assert submit(engine, guagua, ActionType.use_skill.value, skillId="guagua_learned")

    assert engine.current_extra_slot() is None
    assert guagua.sync_attrs["guagua_learned_target_id"] is None
    assert target.current_hp < after_teacher_attack_hp
    assert len(_tagged(flora, "guagua_biyouwoshi")) == 4
    assert any("学会了" in log.message for log in engine.state.battle_log)


def test_serve_tea_moves_teacher_and_buffs_guagua_speed(engine_factory):
    engine = engine_factory(("flora", "guagua", "clawdragon"), ("qiuka", "fanying"))
    guagua = by_template(engine, P1, "guagua")
    flora = by_template(engine, P1, "flora")
    clawdragon = by_template(engine, P1, "clawdragon")

    assert cast_skill(engine, guagua, "guagua_skill1", clawdragon)

    assert not effects_of(flora, EffectType.state_shifu)
    assert effects_of(clawdragon, EffectType.state_shifu)
    speed_buffs = [
        effect for effect in effects_of(guagua, EffectType.buff_stat_percent_boost)
        if effect.stat_type == StatType.speed and effect.value == 0.10
    ]
    assert speed_buffs


def test_baijia_and_xueshen_use_teacher_power(engine_factory):
    engine = engine_factory(("flora", "guagua"), ("qiuka", "fanying"))
    guagua = by_template(engine, P1, "guagua")
    target = by_template(engine, P2, "qiuka")

    before_baijia = target.current_hp
    assert cast_skill(engine, guagua, "guagua_skill2", target)
    assert target.current_hp < before_baijia
    assert any("借师傅" in log.message for log in engine.state.battle_log)

    assert cast_skill(engine, guagua, "guagua_skill3", guagua)
    assert effects_of(guagua, EffectType.state_xueshen)

    before_xueshen = target.current_hp
    assert normal_attack(engine, guagua, target)
    assert target.current_hp < before_xueshen
    assert any("学神不学形" in log.message for log in engine.state.battle_log)
