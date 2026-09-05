from __future__ import annotations

from tests.conftest import P1, P2, by_template, cast_skill, effects_of
from roco.core.battle.effects import add_warmup_stacks, get_warmup_stacks
from roco.core.battle.types import EffectType


def test_warmup_is_added_at_turn_start(engine_factory):
    engine = engine_factory(("steamdragon", "flora", "clawdragon", "chaosling", "starweaver"))
    dragon = by_template(engine, P1, "steamdragon")

    engine.state.active_actor_id = dragon.unique_id
    engine.state.turn_prepared_actor_id = None
    engine.ensure_active_turn_begun()

    assert get_warmup_stacks(dragon) == 1


def test_brand_applies_burn_stacks(engine_factory):
    engine = engine_factory(("steamdragon", "flora", "clawdragon", "chaosling", "starweaver"))
    dragon = by_template(engine, P1, "steamdragon")
    enemy = engine.get_active_spirits(P2)[0]

    assert cast_skill(engine, dragon, "steamdragon_skill1", enemy)

    burn = effects_of(enemy, EffectType.debuff_burn)[0]
    assert burn.source_id == dragon.unique_id
    assert burn.stacks == 6


def test_boil_adds_warmup_stacks(engine_factory):
    engine = engine_factory(("steamdragon", "flora", "clawdragon", "chaosling", "starweaver"))
    dragon = by_template(engine, P1, "steamdragon")
    add_warmup_stacks(dragon, dragon.unique_id, 3)

    assert cast_skill(engine, dragon, "steamdragon_skill3")

    assert get_warmup_stacks(dragon) == 8
