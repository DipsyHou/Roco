"""Stat and effect classification helpers."""

from __future__ import annotations

from typing import Any

from .effect_meta import effect_category, stack_count
from .types import BattleSpirit, EffectType, StatType

_STAT_ENGINE_ATTR = "_stat_engine"


def bind_spirit_stat_engine(spirit: BattleSpirit, engine: Any) -> None:
    setattr(spirit, _STAT_ENGINE_ATTR, engine)


def is_buff_effect(effect_type: EffectType) -> bool:
    return effect_category(effect_type) == "buff"


def is_debuff_effect(effect_type: EffectType) -> bool:
    return effect_category(effect_type) == "debuff"


def is_state_effect(effect_type: EffectType) -> bool:
    return effect_category(effect_type) == "state"


def count_state_effects(spirit: BattleSpirit) -> int:
    return sum(
        1
        for effect in spirit.effects
        if is_state_effect(effect.type)
        and (effect.duration_turns is None or effect.duration_turns != 0)
    )


def get_state_stack_count(spirit: BattleSpirit, eff_type: EffectType) -> int:
    effect = next((e for e in spirit.effects if e.type == eff_type), None)
    return stack_count(effect) if effect else 0


def _stat_base(spirit: BattleSpirit, stat: StatType) -> int:
    if stat == StatType.hp:
        return spirit.base_stats.hp
    if stat == StatType.attack:
        return spirit.base_stats.attack
    if stat == StatType.defense:
        return spirit.base_stats.defense
    if stat == StatType.speed:
        return spirit.base_stats.speed
    raise ValueError(f"unsupported stat: {stat}")


def _conversion_flat_bonus(
    spirit: BattleSpirit,
    stat: StatType,
    engine: Any,
) -> float:
    """Resolve live stat conversions without recursive conversion."""
    bonus = 0.0
    if stat == StatType.attack:
        for effect in spirit.effects:
            if effect.type != EffectType.buff_laziji or not effect.value:
                continue
            source = engine.find_spirit_anywhere(effect.source_id)
            if source and source.is_alive:
                bonus += get_effective_stat(
                    source, StatType.attack, exclude_conversion=True
                ) * effect.value
        for ally in engine.get_all_spirits(spirit.owner_id):
            if not ally.is_alive:
                continue
            for effect in ally.effects:
                if effect.type == EffectType.buff_shuizhuyu and effect.value:
                    bonus += get_effective_stat(
                        ally, StatType.attack, exclude_conversion=True
                    ) * effect.value
    elif stat == StatType.defense:
        for ally in engine.get_all_spirits(spirit.owner_id):
            if not ally.is_alive:
                continue
            for effect in ally.effects:
                if effect.type == EffectType.state_roudun and effect.value:
                    bonus += get_effective_stat(
                        ally, StatType.defense, exclude_conversion=True
                    ) * effect.value
    return bonus


def get_effective_stat(
    spirit: BattleSpirit,
    stat: StatType,
    extra_percent_bonus: float = 0.0,
    *,
    exclude_conversion: bool = False,
) -> float:
    if stat == StatType.hp:
        return float(spirit.max_hp)

    base = _stat_base(spirit, stat)
    percent_sum = 0.0
    flat_sum = 0.0
    for effect in spirit.effects:
        if effect.stat_type != stat or effect.value is None:
            continue
        if effect.type == EffectType.buff_stat_percent_boost:
            percent_sum += effect.value
        elif effect.type in (
            EffectType.debuff_stat_percent_reduction,
            EffectType.debuff_flaw,
        ):
            percent_sum -= effect.value
        elif effect.type == EffectType.buff_stat_flat_boost:
            flat_sum += effect.value
        elif effect.type == EffectType.debuff_stat_flat_reduction:
            flat_sum -= effect.value

    from ..spirits import get_spirit_logic

    logic = get_spirit_logic(spirit.template_id)
    if logic:
        percent_sum += logic.get_stat_percent_bonus(spirit, stat)
    if not exclude_conversion:
        engine = getattr(spirit, _STAT_ENGINE_ATTR, None)
        if engine is not None:
            flat_sum += _conversion_flat_bonus(spirit, stat, engine)

    result = base * (1 + percent_sum + extra_percent_bonus) + flat_sum
    return max(base * 0.2, result)


def get_effective_speed(spirit: BattleSpirit) -> float:
    return get_effective_stat(spirit, StatType.speed)
