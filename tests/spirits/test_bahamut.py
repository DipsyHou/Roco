"""巴哈姆特 基本逻辑冒烟测试."""
from __future__ import annotations

from roco.core.battle.engine import BattleEngine
from roco.core.battle.types import ActionType, EffectType, BattleSpirit
from roco.core.spirits import get_spirit_template
from roco.core.battle.events import DamageEvent, DamageSource, dispatch_damage
from roco.core.battle.damage import get_crit_stats
from roco.core.spirits.bahamut import _add_stacks


P1 = "p1"
P2 = "p2"

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_engine(bahamut_slot: int = 1) -> BattleEngine:
    p1_ids = ["flora"] * 5
    p1_ids[bahamut_slot - 1] = "bahamut"
    return BattleEngine(
        "test-battle", P1, P2,
        [get_spirit_template(tid) for tid in p1_ids],
        [get_spirit_template(tid) for tid in ["flora"] * 5],
    )


def _stacks(spirit: BattleSpirit, eff_type: EffectType) -> int:
    eff = next((e for e in spirit.effects if e.type == eff_type), None)
    return max(0, eff.stacks) if eff else 0


def _has(spirit: BattleSpirit, eff_type: EffectType) -> bool:
    return any(e.type == eff_type for e in spirit.effects)


def _by_id(engine: BattleEngine, template_id: str) -> BattleSpirit:
    for pid in [P1, P2]:
        for s in engine.get_all_spirits(pid):
            if s.template_id == template_id:
                return s
    raise LookupError(template_id)


def _active(engine: BattleEngine) -> BattleSpirit:
    actor_id = engine.state.active_actor_id
    assert actor_id is not None
    return engine.find_spirit_anywhere(actor_id)


def _skip_until(engine: BattleEngine, spirit: BattleSpirit, max_steps: int = 200) -> None:
    """跳过非目标精灵的回合，直到目标精灵成为当前行动者."""
    for _ in range(max_steps):
        if engine.state.phase.value == "finished":
            raise AssertionError("battle ended before target became active")
        if engine.state.active_actor_id == spirit.unique_id:
            return
        actor = _active(engine)
        engine.submit_action(actor.owner_id, {
            "type": ActionType.skip.value,
            "playerId": actor.owner_id,
            "actorId": actor.unique_id,
        })
    raise AssertionError("target did not become active within max_steps")


def _resolve_zhaojia_extra(engine: BattleEngine, bahamut: BattleSpirit) -> None:
    """若招架额外行动已排队，用截拳结算（须指定目标）。"""
    slot = engine.current_extra_slot()
    while slot is not None:
        enemy = engine.get_active_spirits(P2)[0]
        engine.submit_action(bahamut.owner_id, {
            "type": ActionType.use_skill.value,
            "playerId": bahamut.owner_id,
            "actorId": bahamut.unique_id,
            "skillId": "bahamut_zhaojia_jiequan",
            "targetId": enemy.unique_id,
        })
        slot = engine.current_extra_slot()


def _act(engine: BattleEngine, actor: BattleSpirit, **payload) -> bool:
    """向引擎提交行动."""
    payload.setdefault("playerId", actor.owner_id)
    payload.setdefault("actorId", actor.unique_id)
    return engine.submit_action(actor.owner_id, payload)


# ── 开局 ────────────────────────────────────────────────────────────────────


def test_bahamut_starts_with_gangqi_and_chejia_when_leader():
    engine = _make_engine(bahamut_slot=1)
    b = _by_id(engine, "bahamut")
    assert _stacks(b, EffectType.state_gangqi) == 10
    assert _has(b, EffectType.state_chejia)
    assert not _has(b, EffectType.state_cunjin)


def test_bahamut_starts_with_gangqi_and_cunjin_when_not_leader():
    engine = _make_engine(bahamut_slot=3)
    b = _by_id(engine, "bahamut")
    assert _stacks(b, EffectType.state_gangqi) == 10
    assert not _has(b, EffectType.state_chejia)
    assert _has(b, EffectType.state_cunjin)


# ── 彻甲路线：暴击刺客 ──────────────────────────────────────────────────────


def test_chejia_applies_quxie_on_attack():
    engine = _make_engine(bahamut_slot=1)
    b = _by_id(engine, "bahamut")
    enemy = engine.get_active_spirits(P2)[0]
    _skip_until(engine, b)

    _act(engine, b, type=ActionType.normal_attack.value, targetId=enemy.unique_id)

    assert _stacks(enemy, EffectType.state_quxie) == 1
    assert _stacks(b, EffectType.state_gangqi) == 9


def test_chejia_crit_stats_by_quxie_stacks():
    engine = _make_engine(bahamut_slot=1)
    b = _by_id(engine, "bahamut")
    enemy = engine.get_active_spirits(P2)[0]

    _add_stacks(enemy, EffectType.state_quxie, 1, 4, b.unique_id)
    rate, dmg = get_crit_stats(b, enemy)
    assert rate == 0.0
    assert dmg == 100.0

    _add_stacks(enemy, EffectType.state_quxie, 1, 4, b.unique_id)
    rate, dmg = get_crit_stats(b, enemy)
    assert rate == 0.20
    assert dmg == 150.0

    _add_stacks(enemy, EffectType.state_quxie, 1, 4, b.unique_id)
    rate, dmg = get_crit_stats(b, enemy)
    assert rate == 0.30
    assert dmg == 150.0

    _add_stacks(enemy, EffectType.state_quxie, 1, 4, b.unique_id)
    rate, dmg = get_crit_stats(b, enemy)
    assert rate == 0.40
    assert dmg == 150.0


def test_zhaojia_stacks_only_when_already_has_parry():
    engine = _make_engine(bahamut_slot=1)
    b = _by_id(engine, "bahamut")
    attacker = engine.get_active_spirits(P2)[0]

    dispatch_damage(
        engine,
        DamageEvent(attacker, b, 10, source=DamageSource.attack),
    )
    assert _stacks(b, EffectType.state_zhaojia) == 0

    _add_stacks(b, EffectType.state_zhaojia, 1, 5)
    dispatch_damage(
        engine,
        DamageEvent(attacker, b, 10, source=DamageSource.attack),
    )
    assert _stacks(b, EffectType.state_zhaojia) == 2


def test_quxie_capped_at_4():
    engine = _make_engine(bahamut_slot=1)
    b = _by_id(engine, "bahamut")
    enemy = engine.get_active_spirits(P2)[0]

    for _ in range(4):
        _skip_until(engine, b)
        _act(engine, b, type=ActionType.use_skill.value,
             skillId="bahamut_skill1", targetId=enemy.unique_id)

    assert _stacks(enemy, EffectType.state_quxie) == 4
    gangqi_before = _stacks(b, EffectType.state_gangqi)

    _skip_until(engine, b)
    _act(engine, b, type=ActionType.use_skill.value,
         skillId="bahamut_skill1", targetId=enemy.unique_id)

    assert _stacks(enemy, EffectType.state_quxie) == 4  # 不再增加
    assert _stacks(b, EffectType.state_gangqi) == gangqi_before  # 不再消耗


# ── 寸劲路线：反击坦克 ──────────────────────────────────────────────────────


def test_cunjin_applies_zhensha_on_attack():
    engine = _make_engine(bahamut_slot=3)
    b = _by_id(engine, "bahamut")
    enemy = engine.get_active_spirits(P2)[0]
    _skip_until(engine, b)

    _act(engine, b, type=ActionType.normal_attack.value, targetId=enemy.unique_id)

    assert _stacks(enemy, EffectType.state_zhensha) == 1
    assert _stacks(b, EffectType.state_gangqi) == 9


# ── 招架 ────────────────────────────────────────────────────────────────────


def test_yingji_gains_zhaojia():
    engine = _make_engine(bahamut_slot=1)
    b = _by_id(engine, "bahamut")
    _skip_until(engine, b)

    _act(engine, b, type=ActionType.use_skill.value, skillId="bahamut_skill2")

    assert _stacks(b, EffectType.state_zhaojia) == 1


def test_zhaojia_capped_at_5():
    engine = _make_engine(bahamut_slot=1)
    b = _by_id(engine, "bahamut")
    _add_stacks(b, EffectType.state_zhaojia, 5, 5)
    _skip_until(engine, b)

    _act(engine, b, type=ActionType.use_skill.value, skillId="bahamut_skill2")

    assert _stacks(b, EffectType.state_zhaojia) == 5


# ── 龙之舞 ──────────────────────────────────────────────────────────────────


def test_longzhiwu_grants_stats():
    engine = _make_engine(bahamut_slot=1)
    b = _by_id(engine, "bahamut")
    _skip_until(engine, b)

    _act(engine, b, type=ActionType.use_skill.value, skillId="bahamut_skill3")

    buffs = [e for e in b.effects
             if e.type == EffectType.buff_stat_percent_boost and e.display_name == "龙之舞"]
    assert len(buffs) == 2  # 物攻 + 速度


# ── 罡气耗尽 ────────────────────────────────────────────────────────────────


def test_no_marking_when_gangqi_exhausted():
    engine = _make_engine(bahamut_slot=1)
    b = _by_id(engine, "bahamut")
    # 5 个 flora，各打 2 次，共 10 次普攻，正好耗尽 10 罡气且不致死
    enemies = engine.get_active_spirits(P2)
    assert len(enemies) == 5

    for enemy in enemies:
        for _ in range(2):
            _skip_until(engine, b)
            _act(engine, b, type=ActionType.normal_attack.value, targetId=enemy.unique_id)

    assert _stacks(b, EffectType.state_gangqi) == 0

    # 罡气耗尽后再次攻击不应再叠驱邪
    _skip_until(engine, b)
    last_enemy = enemies[-1]
    quxie_before = _stacks(last_enemy, EffectType.state_quxie)
    _act(engine, b, type=ActionType.normal_attack.value, targetId=last_enemy.unique_id)
    assert _stacks(last_enemy, EffectType.state_quxie) == quxie_before
