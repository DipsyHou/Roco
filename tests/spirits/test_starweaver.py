from __future__ import annotations

from tests.conftest import P1, P2, by_template, cast_skill, effects_of, normal_attack, submit
from roco.core.battle.effects import make_effect
from roco.core.battle.types import ActionType, EffectType, StatType


def test_starweaver_uses_personal_energy(engine_factory):
    engine = engine_factory(("starweaver", "flora", "clawdragon", "chaosling", "steamdragon"))
    star = by_template(engine, P1, "starweaver")

    assert star.energy == 4
    assert star.max_energy == 8


def test_purify_removes_debuff_and_adds_immunity(engine_factory):
    engine = engine_factory(("starweaver", "flora", "clawdragon", "chaosling", "steamdragon"))
    star = by_template(engine, P1, "starweaver")
    ally = by_template(engine, P1, "flora")
    ally.effects.append(
        make_effect(
            EffectType.debuff_stat_percent_reduction,
            "x",
            duration_turns=2,
            stat_type=StatType.speed,
            value=0.1,
        )
    )

    assert cast_skill(engine, star, "starweaver_skill2", ally)

    assert not effects_of(ally, EffectType.debuff_stat_percent_reduction)
    immunity = effects_of(ally, EffectType.buff_debuff_immunity)[0]
    assert immunity.duration_turns == 2


def test_burst_consumes_energy_then_self_stuns_and_resets_energy(engine_factory):
    engine = engine_factory(("starweaver", "flora", "clawdragon", "chaosling", "steamdragon"))
    star = by_template(engine, P1, "starweaver")
    star.energy = 6

    assert cast_skill(engine, star, "starweaver_skill3")

    assert star.energy == 4
    assert effects_of(star, EffectType.debuff_stun)[0].duration_turns == 1


def test_resonance_triggers_once_on_ally_single_enemy_skill(engine_factory):
    engine = engine_factory(
        ("qiuka", "starweaver", "flora", "chaosling", "tita"),
        ("clawdragon", "flora", "chaosling", "tita", "fanying"),
    )
    qiuka = by_template(engine, P1, "qiuka")
    star = by_template(engine, P1, "starweaver")
    enemy = by_template(engine, P2, "clawdragon")
    star.energy = 3

    assert cast_skill(engine, qiuka, "qiuka_skill3", enemy)

    assert star.energy == 2
    assert sum(1 for e in engine.state.battle_log if "共振" in e.message) == 1


def test_resonance_triggers_once_on_multi_hit_skill(engine_factory):
    engine = engine_factory(
        ("bahamut", "starweaver", "flora", "chaosling", "tita"),
        ("clawdragon", "flora", "chaosling", "tita", "fanying"),
    )
    bahamut = by_template(engine, P1, "bahamut")
    star = by_template(engine, P1, "starweaver")
    enemy = by_template(engine, P2, "clawdragon")
    star.energy = 4

    assert cast_skill(engine, bahamut, "bahamut_skill1", enemy)

    assert star.energy == 3
    assert sum(1 for e in engine.state.battle_log if "共振" in e.message) == 1


def test_resonance_triggers_once_on_aoe_skill(engine_factory):
    engine = engine_factory(
        ("qiuka", "starweaver", "flora", "chaosling", "tita"),
        ("clawdragon", "flora", "chaosling", "tita", "fanying"),
    )
    qiuka = by_template(engine, P1, "qiuka")
    star = by_template(engine, P1, "starweaver")
    star.energy = 4

    assert cast_skill(engine, qiuka, "qiuka_skill1")

    assert star.energy == 3
    assert sum(1 for e in engine.state.battle_log if "共振" in e.message) == 1


def test_resonance_does_not_trigger_on_ally_skill(engine_factory):
    engine = engine_factory(
        ("flora", "starweaver", "clawdragon", "chaosling", "tita"),
        ("clawdragon", "flora", "chaosling", "tita", "fanying"),
    )
    flora = by_template(engine, P1, "flora")
    star = by_template(engine, P1, "starweaver")
    star.energy = 4

    assert cast_skill(engine, flora, "flora_skill1", star)

    assert star.energy == 4
    assert not any("共振" in e.message for e in engine.state.battle_log)


def test_resonance_does_not_trigger_on_fanying_pull_enemy(engine_factory):
    engine = engine_factory(
        ("fanying", "starweaver", "flora", "chaosling", "tita"),
        ("clawdragon", "flora", "chaosling", "tita", "qiuka"),
    )
    fanying = by_template(engine, P1, "fanying")
    star = by_template(engine, P1, "starweaver")
    enemy = by_template(engine, P2, "clawdragon")
    star.energy = 4

    assert cast_skill(engine, fanying, "fanying_skill3", enemy)

    assert star.energy == 4
    assert not any("共振" in e.message for e in engine.state.battle_log)


def test_resonance_does_not_trigger_on_debuff_only_enemy_skill(engine_factory):
    """无伤害倍率的敌方向技能不算发动攻击（轻雾 / 萌化 / 鬼火）。"""
    cases = (
        ("daermao", "daermao_skill1"),
        ("daermao", "daermao_skill3"),
        ("huxian", "huxian_skill2"),
    )
    for tid, skill_id in cases:
        engine = engine_factory(
            (tid, "starweaver", "flora", "chaosling", "tita"),
            ("clawdragon", "flora", "chaosling", "tita", "fanying"),
        )
        actor = by_template(engine, P1, tid)
        star = by_template(engine, P1, "starweaver")
        enemy = by_template(engine, P2, "clawdragon")
        star.energy = 4

        assert cast_skill(engine, actor, skill_id, enemy), skill_id
        assert star.energy == 4, skill_id
        assert not any("共振" in e.message for e in engine.state.battle_log), skill_id


def test_resonance_triggers_on_ally_normal_attack(engine_factory):
    engine = engine_factory(
        ("flora", "starweaver", "clawdragon", "chaosling", "tita"),
        ("clawdragon", "flora", "chaosling", "tita", "fanying"),
    )
    flora = by_template(engine, P1, "flora")
    star = by_template(engine, P1, "starweaver")
    enemy = by_template(engine, P2, "clawdragon")
    star.energy = 2

    assert normal_attack(engine, flora, enemy)

    assert star.energy == 1


def test_resonance_hits_only_among_attack_launch_targets(engine_factory):
    """蒸汽龙普攻发动目标只有点名者；共振必打该目标，不打溅射邻位。"""
    engine = engine_factory(
        ("steamdragon", "starweaver", "flora", "chaosling", "tita"),
        ("clawdragon", "flora", "chaosling", "tita", "fanying"),
    )
    steam = by_template(engine, P1, "steamdragon")
    star = by_template(engine, P1, "starweaver")
    # 中间槽位，两侧都有邻位可溅射
    p2 = engine.get_active_spirits(P2)
    assert len(p2) >= 3
    main = p2[1]
    neighbors = [p2[0], p2[2]]
    star.energy = 3
    before_main = main.current_hp
    before_n = [n.current_hp for n in neighbors]

    assert normal_attack(engine, steam, main)

    assert star.energy == 2
    assert any("共振" in e.message and main.name in e.message for e in engine.state.battle_log)
    # 共振 40 固伤只落在主目标上（邻位只会受到溅射，HP 降幅应小于主目标那次共振）
    assert main.current_hp <= before_main - 40
    for n, b in zip(neighbors, before_n):
        assert not any(
            "共振" in e.message and n.name in e.message for e in engine.state.battle_log
        )


def test_resonance_damage_comes_after_ally_damage(engine_factory):
    engine = engine_factory(
        ("flora", "starweaver", "clawdragon", "chaosling", "tita"),
        ("clawdragon", "flora", "chaosling", "tita", "fanying"),
    )
    flora = by_template(engine, P1, "flora")
    star = by_template(engine, P1, "starweaver")
    enemy = by_template(engine, P2, "clawdragon")
    star.energy = 2

    assert normal_attack(engine, flora, enemy)

    msgs = [e.message for e in engine.state.battle_log]
    ally_i = next(i for i, m in enumerate(msgs) if "普通攻击" in m or "造成了" in m and flora.name in m)
    reso_i = next(i for i, m in enumerate(msgs) if "共振" in m)
    assert ally_i < reso_i


def test_pulse_deals_mag_ratio_and_gains_energy(engine_factory):
    from roco.core.battle.types import DamageType, StatType
    from roco.core.battle.utils import calculate_damage, get_effective_stat

    engine = engine_factory(("starweaver", "flora", "clawdragon", "chaosling", "steamdragon"))
    star = by_template(engine, P1, "starweaver")
    enemies = engine.get_active_spirits(P2)
    before = [e.current_hp for e in enemies]
    star.energy = 0
    mag = get_effective_stat(star, StatType.mag_atk)
    expected = [
        calculate_damage(mag * 0.20, DamageType.magical, star, e) for e in enemies
    ]

    assert cast_skill(engine, star, "starweaver_skill1")

    assert star.energy == len(enemies)
    assert all(e.current_hp == b - d for e, b, d in zip(enemies, before, expected))


def test_burst_damage_scales_with_mag_atk_and_consumed_energy(engine_factory):
    from roco.core.battle.types import DamageType, StatType
    from roco.core.battle.utils import calculate_damage, get_effective_stat

    engine = engine_factory(("starweaver", "flora", "clawdragon", "chaosling", "steamdragon"))
    star = by_template(engine, P1, "starweaver")
    enemies = engine.get_active_spirits(P2)
    before = [e.current_hp for e in enemies]
    star.energy = 6
    consumed = 6
    ratio = (40 + 5 * consumed) / 100.0
    raw = get_effective_stat(star, StatType.mag_atk) * ratio
    expected = [
        calculate_damage(raw, DamageType.magical, star, enemy) for enemy in enemies
    ]

    assert cast_skill(engine, star, "starweaver_skill3")

    assert star.energy == 4
    assert all(
        e.current_hp == b - d for e, b, d in zip(enemies, before, expected)
    )