from __future__ import annotations

from tests.conftest import P1, P2, by_template, cast_skill, effects_of, make_engine
from roco.core.battle.types import EffectType
from roco.core.battle.formation import living_slot_neighbors


def test_living_slot_neighbors_skips_dead_gaps():
    engine = make_engine(
        ("flora", "clawdragon", "chaosling", "starweaver", "steamdragon"),
        ("qiuka", "fanying", "tita", "guifashi", "cuiding"),
    )
    p1 = engine.get_all_spirits(P1)
    for i, s in enumerate(p1, start=1):
        s.slot = i
    dead = by_template(engine, P1, "starweaver")  # slot 4
    dead.current_hp = 0
    dead.is_alive = False
    anchor = by_template(engine, P1, "chaosling")  # slot 3

    neighbors = living_slot_neighbors(engine.get_active_spirits(P1), anchor)
    ids = {s.template_id for s in neighbors}
    assert ids == {"clawdragon", "steamdragon"}


def test_adjacent_spread_reaches_across_dead_slot(engine_factory):
    engine = engine_factory(
        ("daermao", "flora", "clawdragon", "chaosling", "tita"),
        ("qiuka", "fanying", "steamdragon", "guifashi", "cuiding"),
    )
    dm = by_template(engine, P1, "daermao")
    enemies = engine.get_all_spirits(P2)
    for i, s in enumerate(enemies, start=1):
        s.slot = i
    # 打死 4 号，打 3 号飞霰应扩散到 2 与 5
    slot4 = next(s for s in enemies if s.slot == 4)
    slot4.current_hp = 0
    slot4.is_alive = False
    target = next(s for s in enemies if s.slot == 3)
    left = next(s for s in enemies if s.slot == 2)
    right = next(s for s in enemies if s.slot == 5)

    assert cast_skill(engine, dm, "daermao_skill2", target)

    assert effects_of(target, EffectType.debuff_freeze)
    assert effects_of(left, EffectType.debuff_freeze)
    assert effects_of(right, EffectType.debuff_freeze)
