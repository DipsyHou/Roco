from __future__ import annotations

from roco.core.battle.effects import apply_burn_stacks, apply_poison_stacks, get_total_burn_stacks
from roco.core.battle.types import EffectType
from roco.core.spirits import get_spirit_logic
from tests.conftest import P1, P2, by_template, cast_skill, effects_of


def _cast_huxian_skill(engine, fox, skill_id: str, target) -> None:
    logic = get_spirit_logic("huxian")
    assert logic is not None
    logic.execute_skill(
        engine,
        fox.owner_id,
        fox,
        {"skillId": skill_id, "targetId": target.unique_id},
    )


def test_brand_applies_five_burn_stacks(engine_factory):
    engine = engine_factory(("huxian", "flora", "clawdragon", "chaosling", "starweaver"))
    fox = by_template(engine, P1, "huxian")
    enemy = engine.get_active_spirits(P2)[0]

    assert cast_skill(engine, fox, "huxian_skill1", enemy)

    burn = effects_of(enemy, EffectType.debuff_burn)[0]
    assert burn.source_id == fox.unique_id
    assert burn.stacks == 5


def test_ghost_fire_applies_poison_and_burn(engine_factory):
    engine = engine_factory(("huxian", "flora", "clawdragon", "chaosling", "starweaver"))
    fox = by_template(engine, P1, "huxian")
    enemy = engine.get_active_spirits(P2)[0]

    _cast_huxian_skill(engine, fox, "huxian_skill2", enemy)

    assert effects_of(enemy, EffectType.debuff_poison)[0].stacks == 4
    assert effects_of(enemy, EffectType.debuff_burn)[0].stacks == 4


def test_implosion_triggers_poison_when_granting_burn(engine_factory):
    engine = engine_factory(("huxian", "flora", "clawdragon", "chaosling", "starweaver"))
    fox = by_template(engine, P1, "huxian")
    enemy = engine.get_active_spirits(P2)[0]
    apply_poison_stacks(enemy, fox.unique_id, 4)
    hp_before = enemy.current_hp

    _cast_huxian_skill(engine, fox, "huxian_skill1", enemy)

    assert enemy.current_hp < hp_before
    assert effects_of(enemy, EffectType.debuff_burn)[0].stacks == 5
    assert effects_of(enemy, EffectType.debuff_poison)[0].stacks == 4


def test_implosion_triggers_all_burn_sources_when_granting_poison(engine_factory):
    engine = engine_factory(("huxian", "steamdragon", "clawdragon", "chaosling", "starweaver"))
    fox = by_template(engine, P1, "huxian")
    steam = by_template(engine, P1, "steamdragon")
    enemy = engine.get_active_spirits(P2)[0]
    apply_burn_stacks(enemy, steam.unique_id, 4)
    apply_burn_stacks(enemy, fox.unique_id, 6)
    hp_before = enemy.current_hp

    _cast_huxian_skill(engine, fox, "huxian_skill2", enemy)

    assert enemy.current_hp < hp_before
    assert effects_of(enemy, EffectType.debuff_poison)[0].stacks == 4
    assert get_total_burn_stacks(enemy) == 14
    fox_burn = next(e for e in effects_of(enemy, EffectType.debuff_burn) if e.source_id == fox.unique_id)
    steam_burn = next(e for e in effects_of(enemy, EffectType.debuff_burn) if e.source_id == steam.unique_id)
    assert fox_burn.stacks == 10
    assert steam_burn.stacks == 4


def test_fan_wind_splashes_burn_to_adjacent(engine_factory):
    engine = engine_factory(("huxian", "flora", "clawdragon", "chaosling", "starweaver"))
    fox = by_template(engine, P1, "huxian")
    enemies = engine.get_active_spirits(P2)
    if len(enemies) < 2:
        return
    target = enemies[0]
    adjacent = next(
        (e for e in enemies if e.unique_id != target.unique_id and abs(e.slot - target.slot) == 1),
        None,
    )
    if adjacent is None:
        return

    _cast_huxian_skill(engine, fox, "huxian_skill3", target)

    assert effects_of(target, EffectType.debuff_burn)[0].stacks == 4
    assert effects_of(adjacent, EffectType.debuff_burn)[0].stacks == 2
