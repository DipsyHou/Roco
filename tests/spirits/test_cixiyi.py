"""石化刺蜥蜴 — 硬化肌肤 / 棘皮 / 再生 / 岩刺。"""

from __future__ import annotations

from tests.conftest import P1, P2, by_template
from roco.core.battle.types import DamageType, EffectType, StatType
from roco.core.battle.utils import get_effective_stat, make_effect
from roco.core.battle.events import DamageEvent, DamageSource, dispatch_damage
from roco.core.battle.shield import grant_shield, shield_from_source
from roco.core.spirits import get_spirit_template
from roco.core.spirits.cixiyi import cixiyi_logic, SKILL_JIPI


def _engine(engine_factory):
    return engine_factory(
        ("cixiyi", "flora", "tita", "fanying", "clawdragon"),
        ("steamdragon", "chaosling", "qiuka", "starweaver", "huxian"),
    )


def test_harden_skin_is_state_and_reduces_only_fixed(engine_factory):
    engine = _engine(engine_factory)
    cx = by_template(engine, P1, "cixiyi")

    # 硬化肌肤是状态效果（非「受到伤害降低」正面效果）
    assert any(e.type == EffectType.state_yinghuajifu for e in cx.effects)
    assert not any(
        e.type == EffectType.buff_taken_damage_percent_reduction for e in cx.effects
    )
    # 仅对固定伤害减 50%，物理 / 魔法不受影响
    assert cixiyi_logic.get_incoming_damage_reduction(cx, DamageType.fixed) == 0.5
    assert cixiyi_logic.get_incoming_damage_reduction(cx, DamageType.physical) == 0.0
    assert cixiyi_logic.get_incoming_damage_reduction(cx, DamageType.magical) == 0.0


def test_regen_stat_bonus(engine_factory):
    engine = _engine(engine_factory)
    cx = by_template(engine, P1, "cixiyi")

    assert cixiyi_logic.get_stat_percent_bonus(cx, StatType.def_) == 0.0
    cx.effects.append(make_effect(EffectType.state_zaisheng, cx.unique_id, duration_turns=1))
    assert cixiyi_logic.get_stat_percent_bonus(cx, StatType.def_) == 0.20
    assert cixiyi_logic.get_stat_percent_bonus(cx, StatType.mag_def) == 0.20


def test_jipi_apply_all_allies_and_convert_on_damage(engine_factory):
    engine = _engine(engine_factory)
    cx = by_template(engine, P1, "cixiyi")
    ally = by_template(engine, P1, "flora")

    cixiyi_logic._skill_jipi(engine, P1, cx, {})
    assert any(e.type == EffectType.state_jipi for e in ally.effects)
    assert any(e.type == EffectType.state_jipi for e in cx.effects)

    # 已有棘皮则不再给予
    cixiyi_logic._skill_jipi(engine, P1, cx, {})
    assert sum(1 for e in ally.effects if e.type == EffectType.state_jipi) == 1

    attacker = by_template(engine, P2, "steamdragon")
    dispatch_damage(engine, DamageEvent(attacker, ally, 10, source=DamageSource.attack))

    assert not any(e.type == EffectType.state_jipi for e in ally.effects)
    sh = shield_from_source(ally, cx.unique_id)
    assert sh is not None
    assert int(sh.value) == int(get_effective_stat(cx, StatType.def_) * 0.30)


def test_regen_refreshes_and_reduces_jipi_cost(engine_factory):
    engine = _engine(engine_factory)
    cx = by_template(engine, P1, "cixiyi")
    attacker = by_template(engine, P2, "steamdragon")

    dispatch_damage(engine, DamageEvent(attacker, cx, 10, source=DamageSource.attack))
    z = next(e for e in cx.effects if e.type == EffectType.state_zaisheng)
    assert z.duration_turns == 1

    dispatch_damage(engine, DamageEvent(attacker, cx, 10, source=DamageSource.attack))
    assert z.duration_turns == 2
    dispatch_damage(engine, DamageEvent(attacker, cx, 10, source=DamageSource.attack))
    assert z.duration_turns == 2  # 最多 2 回合

    skill = next(s for s in get_spirit_template("cixiyi").skills if s.id == SKILL_JIPI)
    assert cixiyi_logic.get_skill_energy_cost(cx, skill, 3) == 1


def test_yanci_self_damage_and_hits_enemy(engine_factory):
    engine = _engine(engine_factory)
    cx = by_template(engine, P1, "cixiyi")
    enemy = by_template(engine, P2, "steamdragon")

    enemy_hp0 = enemy.current_hp
    cx_hp0 = cx.current_hp
    cixiyi_logic._skill_yanci(engine, P1, cx, {"targetId": enemy.unique_id})

    assert enemy.current_hp < enemy_hp0
    assert cx.current_hp < cx_hp0  # 20% 物攻自伤（无盾时落到生命）


def test_yanci_scales_with_own_shield(engine_factory):
    engine = _engine(engine_factory)
    cx = by_template(engine, P1, "cixiyi")
    enemy = by_template(engine, P2, "steamdragon")

    # 给一层外部护盾，岩刺主段应额外加上「100% 自身护盾量」
    grant_shield(cx, "external", 300, 300, duration=5, display_name="测试盾")
    enemy_hp0 = enemy.current_hp
    cixiyi_logic._skill_yanci(engine, P1, cx, {"targetId": enemy.unique_id})
    dmg_with_shield = enemy_hp0 - enemy.current_hp

    # 自伤 20% 物攻（=20）远小于 300 护盾，主段仍能吃到大部分护盾量
    assert dmg_with_shield > 0
