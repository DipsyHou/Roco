from __future__ import annotations

from tests.conftest import P1, P2, by_template, cast_skill, normal_attack
from roco.core.battle.hp import apply_damage
from roco.core.battle.types import DamageType, EffectType, StatType
from roco.core.battle.utils import calculate_damage, get_effective_stat, make_effect
from roco.core.spirits import get_spirit_template
from roco.core.spirits.xiaozong import (
    add_lingqi,
    clear_lingqi,
    get_lingqi_stacks,
    grant_tongling,
    has_tongling,
    xiaozong_logic,
)

TEAM = ("xiaozong", "flora", "clawdragon", "chaosling", "starweaver")
# 星织者共振会在友方普攻后追加固伤，测伤害时用不含星织者的阵容。
TEAM_NO_STARWEAVER = ("xiaozong", "flora", "clawdragon", "chaosling", "flora")


def _xz(engine):
    return by_template(engine, P1, "xiaozong")


# --- 灵气上限 / 被动减伤 ---------------------------------------------------

def test_lingqi_cap_locked_at_battle_start(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    assert xz.battle_start_max_hp == xz.max_hp

    # 局内降低生命上限后，灵气上限仍按开局上限。
    xz.max_hp = 100
    add_lingqi(xz, 10_000)
    assert get_lingqi_stacks(xz) == xz.battle_start_max_hp


def _calc_physical(engine, xz, amount: int) -> int:
    attacker = engine.get_active_spirits(P2)[0]
    xz.base_stats.def_ = 100
    return calculate_damage(amount, DamageType.physical, attacker, xz)


def _calc_fixed(engine, xz, amount: int) -> int:
    attacker = engine.get_active_spirits(P2)[0]
    return calculate_damage(amount, DamageType.fixed, attacker, xz)


def test_lingjue_reduces_damage_and_grants_lingqi(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    add_lingqi(xz, 50)

    # floor(50 * 0.1) = 5
    assert _calc_physical(engine, xz, 100) == 95
    assert get_lingqi_stacks(xz) == 55


def test_lingjue_in_tongling_reduces_but_no_grant(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    add_lingqi(xz, 50)
    grant_tongling(xz)

    assert _calc_physical(engine, xz, 100) == 95
    assert get_lingqi_stacks(xz) == 50  # 通灵后不再积攒


def test_lingjue_lingqi_gain_equals_actual_reduction(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    add_lingqi(xz, 300)

    # 灵珏可减 30，段伤害 24 → 实际减 24、叠 24 层（非 30）。
    assert _calc_physical(engine, xz, 24) == 0
    assert get_lingqi_stacks(xz) == 324


def test_lingjue_no_lingqi_on_zero_damage_segment(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    add_lingqi(xz, 300)

    assert _calc_physical(engine, xz, 0) == 0
    assert get_lingqi_stacks(xz) == 300


def test_lingjue_no_effect_below_ten_stacks(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    add_lingqi(xz, 9)

    assert _calc_physical(engine, xz, 100) == 100
    assert get_lingqi_stacks(xz) == 9


def test_lingjue_does_not_reduce_fixed_damage(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    add_lingqi(xz, 300)

    assert _calc_fixed(engine, xz, 24) == 24
    assert get_lingqi_stacks(xz) == 300


def test_lingjue_reduces_without_generic_flat_debuff(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    add_lingqi(xz, 300)
    xz.effects.append(
        make_effect(
            EffectType.buff_taken_damage_flat_reduction,
            xz.unique_id,
            value=5,
        )
    )

    # 固定值减伤效果已取消；灵珏也不减固伤。
    assert _calc_fixed(engine, xz, 24) == 24
    assert get_lingqi_stacks(xz) == 300


# --- 通灵复活 -------------------------------------------------------------

def test_fatal_hit_revives_with_tongling(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    add_lingqi(xz, 40)
    xz.current_hp = 10

    dmg = _calc_fixed(engine, xz, 9999)
    apply_damage(xz, dmg, ctx=engine)

    # 固伤不吃灵珏减伤；40 层灵气复活续命至 40。
    assert xz.is_alive
    assert xz.current_hp == 40
    assert get_lingqi_stacks(xz) == 40
    assert has_tongling(xz)


def test_second_fatal_hit_after_tongling_kills(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    add_lingqi(xz, 40)
    xz.current_hp = 10
    dmg = _calc_fixed(engine, xz, 9999)
    apply_damage(xz, dmg, ctx=engine)
    assert xz.is_alive

    apply_damage(xz, 9999, ctx=engine)
    assert not xz.is_alive


def test_no_revive_without_lingqi(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    clear_lingqi(xz)
    xz.current_hp = 10

    apply_damage(xz, 9999, ctx=engine)

    assert not xz.is_alive
    assert not has_tongling(xz)


# --- 普攻双形态 -----------------------------------------------------------

def test_tongling_normal_attack_consumes_thirty(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    grant_tongling(xz)
    add_lingqi(xz, 40)
    enemy = engine.get_active_spirits(P2)[0]

    assert normal_attack(engine, xz, enemy)
    assert get_lingqi_stacks(xz) == 10  # 40 - 30


def test_tongling_normal_attack_below_thirty_uses_tongling_version(engine_factory):
    engine = engine_factory(TEAM_NO_STARWEAVER, TEAM_NO_STARWEAVER)
    xz = _xz(engine)
    grant_tongling(xz)
    add_lingqi(xz, 20)
    enemy = engine.get_active_spirits(P2)[0]
    hp_before = enemy.current_hp

    assert normal_attack(engine, xz, enemy)
    assert get_lingqi_stacks(xz) == 0
    dealt = hp_before - enemy.current_hp
    expected_mag = calculate_damage(
        get_effective_stat(xz, StatType.mag_atk) * 1.0,
        DamageType.magical,
        xz,
        enemy,
    )
    expected_phys = calculate_damage(
        get_effective_stat(xz, StatType.atk) * 1.0,
        DamageType.physical,
        xz,
        enemy,
    )
    assert dealt == expected_mag
    assert expected_mag != expected_phys


def test_tongling_normal_attack_zero_lingqi_still_tongling(engine_factory):
    engine = engine_factory(TEAM_NO_STARWEAVER, TEAM_NO_STARWEAVER)
    xz = _xz(engine)
    grant_tongling(xz)
    enemy = engine.get_active_spirits(P2)[0]
    hp_before = enemy.current_hp

    assert normal_attack(engine, xz, enemy)
    assert get_lingqi_stacks(xz) == 0
    dealt = hp_before - enemy.current_hp
    expected_mag = calculate_damage(
        get_effective_stat(xz, StatType.mag_atk) * 1.0,
        DamageType.magical,
        xz,
        enemy,
    )
    assert dealt == expected_mag


def test_normal_attack_without_tongling_keeps_lingqi(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    add_lingqi(xz, 25)
    enemy = engine.get_active_spirits(P2)[0]

    assert normal_attack(engine, xz, enemy)
    assert get_lingqi_stacks(xz) == 25  # 普通版不消耗灵气


# --- 技能 -----------------------------------------------------------------

def test_riyue_grants_lingqi_and_hits_adjacent(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    enemies = engine.get_active_spirits(P2)
    target = enemies[1]  # slot 2，确保有相邻
    before = [e.current_hp for e in enemies]

    assert cast_skill(engine, xz, "xiaozong_skill1", target)

    assert get_lingqi_stacks(xz) == 30
    after = [e.current_hp for e in enemies]
    assert after[1] < before[1]
    # 至少一个相邻精灵受伤
    assert any(after[i] < before[i] for i in (0, 2) if i < len(enemies))


def test_huacai_tongling_heals(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    grant_tongling(xz)
    add_lingqi(xz, 60)
    xz.current_hp = 100
    enemy = engine.get_active_spirits(P2)[0]

    assert cast_skill(engine, xz, "xiaozong_skill2", enemy)

    assert xz.current_hp > 100  # 通灵华采回血
    assert get_lingqi_stacks(xz) == 30  # 60 - 30


def test_yuanju_reduces_skill_cost(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    tpl = get_spirit_template("xiaozong")
    skill1, skill2, skill3 = tpl.skills

    assert cast_skill(engine, xz, "xiaozong_skill3")

    assert engine.effective_skill_energy_cost(xz, skill1) == 2
    assert engine.effective_skill_energy_cost(xz, skill2) == 2
    assert engine.effective_skill_energy_cost(xz, skill3) == 3
    assert get_lingqi_stacks(xz) == 30
    mitigations = [
        e
        for e in xz.effects
        if e.type == EffectType.buff_taken_damage_percent_reduction
    ]
    assert len(mitigations) == 1
    assert mitigations[0].value == 0.10


def test_yuanju_refreshes_buffs_without_stacking(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    tpl = get_spirit_template("xiaozong")
    skill1 = tpl.skills[0]

    assert cast_skill(engine, xz, "xiaozong_skill3")
    mit = next(
        e
        for e in xz.effects
        if e.type == EffectType.buff_taken_damage_percent_reduction
    )
    cost1 = next(
        e
        for e in xz.effects
        if e.type == EffectType.buff_skill_energy_cost_reduction
        and e.effect_tag == skill1.id
    )
    mit.duration_turns = 1
    cost1.duration_turns = 1

    assert cast_skill(engine, xz, "xiaozong_skill3")

    assert len(
        [
            e
            for e in xz.effects
            if e.type == EffectType.buff_taken_damage_percent_reduction
        ]
    ) == 1
    # 刷新为 3 回合后，本回合结束会各 -1。
    assert mit.duration_turns == 2
    assert mit.value == 0.10
    cost_buffs = [
        e
        for e in xz.effects
        if e.type == EffectType.buff_skill_energy_cost_reduction
    ]
    assert len(cost_buffs) == 2
    assert all(e.duration_turns == 2 for e in cost_buffs)
    assert get_lingqi_stacks(xz) == 60


def test_yuanju_tongling_below_thirty_consumes_all(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    grant_tongling(xz)
    add_lingqi(xz, 20)

    assert cast_skill(engine, xz, "xiaozong_skill3")

    mit = next(
        e
        for e in xz.effects
        if e.type == EffectType.buff_taken_damage_percent_reduction
    )
    assert mit.value == 0.15
    assert get_lingqi_stacks(xz) == 0


def test_yuanju_tongling_30_mitigation(engine_factory):
    engine = engine_factory(TEAM)
    xz = _xz(engine)
    grant_tongling(xz)
    add_lingqi(xz, 60)

    assert cast_skill(engine, xz, "xiaozong_skill3")

    mit = next(
        e
        for e in xz.effects
        if e.type == EffectType.buff_taken_damage_percent_reduction
    )
    assert mit.value == 0.15
    assert get_lingqi_stacks(xz) == 30
