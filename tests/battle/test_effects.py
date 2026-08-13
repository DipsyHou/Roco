from __future__ import annotations

import pytest

from roco.core.battle.effects import (
    apply_burn_stacks,
    apply_poison_stacks,
    make_effect,
    tick_effects,
)
from roco.core.battle.effect_display import format_spirit_effects
from roco.core.battle.stats import count_state_effects, get_state_stack_count
from roco.core.battle.types import EffectType, StatType


def test_duration_effect_ticks_down_and_expires(standard_engine):
    spirit = standard_engine.get_all_spirits("p1")[0]
    spirit.effects.append(
        make_effect(EffectType.debuff_stun, "src", duration_turns=2)
    )

    assert tick_effects(spirit) == []
    assert spirit.effects[0].duration_turns == 1
    expired = tick_effects(spirit)

    assert expired[0].type == EffectType.debuff_stun
    assert spirit.effects == []


def test_permanent_effect_and_stack_effects_do_not_tick(standard_engine):
    spirit = standard_engine.get_all_spirits("p1")[0]
    spirit.effects.extend(
        [
            make_effect(
                EffectType.buff_stat_percent_boost,
                "src",
                stat_type=StatType.atk,
                value=0.1,
            ),
            make_effect(EffectType.state_warmup, "src", stacks=3),
        ]
    )

    assert tick_effects(spirit) == []

    permanent, warmup = spirit.effects
    assert permanent.duration_turns is None
    assert warmup.stacks == 3


def test_state_count_and_stack_count_use_separate_fields(standard_engine):
    spirit = standard_engine.get_all_spirits("p1")[0]
    spirit.effects.extend(
        [
            make_effect(EffectType.state_warmup, "src", stacks=4),
            make_effect(EffectType.state_shunt, "src", stacks=1),
        ]
    )

    assert count_state_effects(spirit) == 2
    assert get_state_stack_count(spirit, EffectType.state_warmup) == 4


@pytest.mark.parametrize(
    ("effect_type", "expected"),
    [
        (EffectType.state_warmup, "[state]升温 * 3"),
        (EffectType.debuff_poison, "[debuff]中毒 * 3"),
    ],
)
def test_stack_display_uses_stacks_not_duration(effect_type, expected):
    effect = make_effect(effect_type, "src", duration_turns=9, stacks=3)

    assert format_spirit_effects([effect], {"src": "source"}) == [expected]


def test_debuff_immunity_blocks_poison_and_burn(standard_engine):
    target = standard_engine.get_all_spirits("p2")[0]
    target.effects.append(make_effect(EffectType.buff_debuff_immunity, "src", duration_turns=1))

    assert not apply_poison_stacks(target, "poisoner", 3)
    assert not apply_burn_stacks(target, "burner", 3)
    assert not any(e.type in (EffectType.debuff_poison, EffectType.debuff_burn) for e in target.effects)
