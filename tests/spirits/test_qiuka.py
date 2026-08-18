from __future__ import annotations

import pytest

from tests.conftest import P1, P2, by_template, cast_skill, effects_of, normal_attack
from roco.core.battle.types import EffectType
from roco.core.spirits.qiuka import QiukaLogic


def test_damage_log_precedes_guardian(engine_factory):
    engine = engine_factory(
        ("qiuka", "flora", "chaosling", "tita", "steamdragon"),
        ("clawdragon", "flora", "chaosling", "tita", "fanying"),
    )
    qiuka = by_template(engine, P1, "qiuka")
    claw = by_template(engine, P2, "clawdragon")

    start = len(engine.state.battle_log)
    QiukaLogic()._hit_physical(engine, qiuka, claw, 0.20, "用毒刺对")

    messages = [entry.message for entry in engine.state.battle_log[start:]]
    sting_idx = next(i for i, message in enumerate(messages) if "毒刺" in message)
    guardian_idx = next(i for i, message in enumerate(messages) if "守护者" in message)
    assert sting_idx < guardian_idx


def test_poison_sting_adds_poison_to_enemies(engine_factory):
    engine = engine_factory(("qiuka", "flora", "clawdragon", "chaosling", "starweaver"))
    qiuka = by_template(engine, P1, "qiuka")

    assert cast_skill(engine, qiuka, "qiuka_skill1")

    assert any(effects_of(enemy, EffectType.debuff_poison) for enemy in engine.get_active_spirits(P2))


def test_virulent_adds_poison_and_triggers_damage_without_decreasing(engine_factory):
    engine = engine_factory(("qiuka", "flora", "clawdragon", "chaosling", "starweaver"))
    qiuka = by_template(engine, P1, "qiuka")
    enemy = engine.get_active_spirits(P2)[0]
    hp_before = enemy.current_hp

    assert cast_skill(engine, qiuka, "qiuka_skill2", enemy)

    poison = effects_of(enemy, EffectType.debuff_poison)[0]
    assert poison.stacks == 4
    assert enemy.current_hp < hp_before


def test_poisoned_target_takes_more_poison_claw_damage(engine_factory):
    engine = engine_factory(("qiuka", "flora", "clawdragon", "chaosling", "starweaver"))
    qiuka = by_template(engine, P1, "qiuka")
    enemy = engine.get_active_spirits(P2)[0]
    assert cast_skill(engine, qiuka, "qiuka_skill2", enemy)
    hp_before = enemy.current_hp

    assert cast_skill(engine, qiuka, "qiuka_skill3", enemy)

    assert enemy.current_hp < hp_before


def test_poison_claw_counts_at_most_ten_stacks(engine_factory):
    from unittest.mock import patch

    engine = engine_factory(("qiuka", "flora", "clawdragon", "chaosling", "starweaver"))
    qiuka = by_template(engine, P1, "qiuka")
    enemy = engine.get_active_spirits(P2)[0]
    from roco.core.battle.effects import apply_poison_stacks

    apply_poison_stacks(enemy, qiuka.unique_id, 15)
    ratios: list[float] = []

    real_deal = QiukaLogic._hit_physical

    def spy(self, ctx, actor, target, ratio, verb):
        ratios.append(ratio)
        return real_deal(self, ctx, actor, target, ratio, verb)

    with patch.object(QiukaLogic, "_hit_physical", spy):
        QiukaLogic()._skill_poison_claw(engine, P1, qiuka, {"targetId": enemy.unique_id})

    # 痛苦被动在 _hit_physical 内再 ×1.25，技能侧传入倍率应封顶为 0.8 + 0.16×10
    assert ratios == [pytest.approx(2.4)]


def test_poison_claw_triggers_poison_after_hit(engine_factory):
    engine = engine_factory(("qiuka", "flora", "clawdragon", "chaosling", "starweaver"))
    qiuka = by_template(engine, P1, "qiuka")
    enemy = engine.get_active_spirits(P2)[0]
    from roco.core.battle.effects import apply_poison_stacks
    from roco.core.battle.utils import get_poison_stacks

    apply_poison_stacks(enemy, qiuka.unique_id, 4)
    stacks_before = get_poison_stacks(enemy)
    hp_before = enemy.current_hp

    # 直接调技能逻辑，避开行动结束时中毒减层
    QiukaLogic()._skill_poison_claw(engine, P1, qiuka, {"targetId": enemy.unique_id})

    assert get_poison_stacks(enemy) == stacks_before
    assert enemy.current_hp < hp_before
    assert any(
        e.data
        and e.data.get("effectType") == EffectType.debuff_poison.value
        and e.data.get("targetId") == enemy.unique_id
        for e in engine.state.battle_log
    )
