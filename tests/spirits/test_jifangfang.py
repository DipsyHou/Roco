"""机械方方 — 多色模块 / 防火墙 / 便携防火墙 / 超限模块。"""

from __future__ import annotations

from tests.conftest import P1, by_template
from roco.core.battle.types import EffectType, StatType
from roco.core.battle.utils import get_effective_stat, make_effect
from roco.core.battle.shield import shield_from_source
from roco.core.spirits.jifangfang import jifangfang_logic


def _engine(engine_factory):
    return engine_factory(
        ("jifangfang", "flora", "tita", "fanying", "clawdragon"),
        ("steamdragon", "chaosling", "qiuka", "starweaver", "huxian"),
    )


def _damage_bonus(engine, source, holder):
    return jifangfang_logic.get_aura_damage_percent_bonus(engine, source, holder)


def _taken_reduction(engine, source, holder):
    return jifangfang_logic.get_aura_taken_damage_reduction(engine, source, holder)


def _speed_bonus(engine, source, holder):
    return jifangfang_logic.get_aura_stat_percent_bonus(
        engine, source, holder, StatType.speed
    )


def test_starts_with_qianghua_and_rotates_on_skill(engine_factory):
    engine = _engine(engine_factory)
    ff = by_template(engine, P1, "jifangfang")
    assert any(e.type == EffectType.state_module_qianghua for e in ff.effects)

    jifangfang_logic.on_action_end(
        engine, P1, ff, {"skillId": "jifangfang_skill2"}, stunned=False
    )
    assert any(e.type == EffectType.state_module_jisu for e in ff.effects)
    assert not any(e.type == EffectType.state_module_qianghua for e in ff.effects)

    # 普通攻击（无 skillId）不轮转
    jifangfang_logic.on_action_end(engine, P1, ff, {"targetId": "x"}, stunned=False)
    assert any(e.type == EffectType.state_module_jisu for e in ff.effects)


def test_fanghuoqiang_shield_and_bianxie_merge(engine_factory):
    engine = _engine(engine_factory)
    ff = by_template(engine, P1, "jifangfang")
    ally = by_template(engine, P1, "flora")
    atk = get_effective_stat(ff, StatType.atk)

    jifangfang_logic._skill_fanghuoqiang(engine, P1, ff, {})
    sh = shield_from_source(ally, ff.unique_id)
    assert sh is not None and int(sh.value) == int(atk * 0.60)
    assert shield_from_source(ff, ff.unique_id) is not None  # 含自身

    before = int(shield_from_source(ally, ff.unique_id).value)
    jifangfang_logic._skill_bianxie(engine, P1, ff, {"targetId": ally.unique_id})
    after = int(shield_from_source(ally, ff.unique_id).value)
    assert after == min(int(atk * 1.20), before + int(atk * 0.30))


def test_module_aura_only_for_shield_holders(engine_factory):
    engine = _engine(engine_factory)
    ff = by_template(engine, P1, "jifangfang")
    ally = by_template(engine, P1, "flora")

    # 未持有护盾者不吃光环
    assert _damage_bonus(engine, ff, ally) == 0.0
    jifangfang_logic._skill_fanghuoqiang(engine, P1, ff, {})
    assert _damage_bonus(engine, ff, ally) == 0.12  # 开局强化模块
    assert _taken_reduction(engine, ff, ally) == 0.0

    ff.effects = [e for e in ff.effects if e.type != EffectType.state_module_qianghua]
    ff.effects.append(make_effect(EffectType.state_module_diyu, ff.unique_id))
    assert _taken_reduction(engine, ff, ally) == 0.12
    assert _damage_bonus(engine, ff, ally) == 0.0


def test_chaoxian_enables_all_three(engine_factory):
    engine = _engine(engine_factory)
    ff = by_template(engine, P1, "jifangfang")
    ally = by_template(engine, P1, "flora")

    jifangfang_logic._skill_fanghuoqiang(engine, P1, ff, {})
    jifangfang_logic._skill_chaoxian(engine, P1, ff, {})
    assert _damage_bonus(engine, ff, ally) == 0.12
    assert _speed_bonus(engine, ff, ally) == 0.06
    assert _taken_reduction(engine, ff, ally) == 0.12
