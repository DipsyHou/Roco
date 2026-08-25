"""护盾机制 — 并行抵扣 / 来源归并 / 方案B上限（见 docs/mechanics.md §22）。"""

from __future__ import annotations

from tests.conftest import P2, by_template
from roco.core.battle.types import EffectType
from roco.core.battle.utils import make_effect
from roco.core.battle.hp import apply_damage
from roco.core.battle.shield import (
    absorb,
    grant_shield,
    shield_from_source,
    total_shield,
)


def _target(engine_factory):
    engine = engine_factory(
        ("cixiyi", "flora", "tita", "fanying", "clawdragon"),
        ("steamdragon", "chaosling", "qiuka", "starweaver", "huxian"),
    )
    target = by_template(engine, P2, "steamdragon")
    target.effects = [e for e in target.effects if e.type != EffectType.state_shield]
    return engine, target


def _set_shields(target, a, b) -> None:
    target.effects = [e for e in target.effects if e.type != EffectType.state_shield]
    if a is not None:
        target.effects.append(
            make_effect(EffectType.state_shield, "A", value=a, duration_turns=5)
        )
    if b is not None:
        target.effects.append(
            make_effect(EffectType.state_shield, "B", value=b, duration_turns=5)
        )


def test_parallel_absorb_doc_example(engine_factory):
    _, target = _target(engine_factory)

    _set_shields(target, 100, 50)
    assert absorb(target, 30) == 0
    assert int(shield_from_source(target, "A").value) == 70
    assert int(shield_from_source(target, "B").value) == 20

    _set_shields(target, 100, 50)
    assert absorb(target, 80) == 0
    assert int(shield_from_source(target, "A").value) == 20
    assert shield_from_source(target, "B") is None

    _set_shields(target, 100, 50)
    assert absorb(target, 120) == 20
    assert shield_from_source(target, "A") is None
    assert shield_from_source(target, "B") is None


def test_grant_plan_b_cap_no_retroactive_shave(engine_factory):
    _, target = _target(engine_factory)

    assert grant_shield(target, "s", 100, 120, duration=3) == 100
    assert int(shield_from_source(target, "s").value) == 100
    # 累积并以当前上限封顶
    assert grant_shield(target, "s", 50, 120, duration=3) == 20
    assert int(shield_from_source(target, "s").value) == 120
    # 上限降到低于已有盾：加不进去，但已有盾不被削减
    assert grant_shield(target, "s", 30, 80, duration=3) == 0
    assert int(shield_from_source(target, "s").value) == 120


def test_total_shield_sums_all_sources(engine_factory):
    _, target = _target(engine_factory)
    grant_shield(target, "a", 30, 100, duration=3)
    grant_shield(target, "b", 20, 100, duration=3)
    assert total_shield(target) == 50


def test_apply_damage_absorbs_but_still_counts(engine_factory):
    engine, target = _target(engine_factory)
    grant_shield(target, "s", 50, 100, duration=3)
    hp0 = target.current_hp

    reported = apply_damage(target, 30, ctx=engine)
    assert reported == 30  # 仍算「受到伤害」
    assert target.current_hp == hp0  # 完全被护盾抵扣
    assert int(shield_from_source(target, "s").value) == 20

    apply_damage(target, 40, ctx=engine)
    assert target.current_hp == hp0 - 20  # 40 - 20(盾) = 20 落到生命
    assert shield_from_source(target, "s") is None
