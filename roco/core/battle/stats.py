"""Stat and effect classification helpers."""

from __future__ import annotations

from typing import Any, Optional

from .effect_meta import effect_category, stack_count
from .types import BattleSpirit, EffectType, StatType

# Set by BattleEngine so live conversion buffs can resolve source / aura carriers.
_STAT_ENGINE_ATTR = "_stat_engine"


def bind_spirit_stat_engine(spirit: BattleSpirit, engine: Any) -> None:
    setattr(spirit, _STAT_ENGINE_ATTR, engine)


def is_buff_effect(effect_type: EffectType) -> bool:
    """Return whether an effect type is a positive buff."""
    return effect_category(effect_type) == "buff"


def is_debuff_effect(effect_type: EffectType) -> bool:
    """Return whether an effect type is negative."""
    return effect_category(effect_type) == "debuff"


def is_state_effect(effect_type: EffectType) -> bool:
    """Return whether an effect type is a state effect."""
    return effect_category(effect_type) == "state"


def count_state_effects(spirit: BattleSpirit) -> int:
    """Count active ``state_*`` effects stored on the spirit."""
    return sum(
        1
        for effect in spirit.effects
        if is_state_effect(effect.type)
        and (effect.duration_turns is None or effect.duration_turns != 0)
    )


def get_state_stack_count(spirit: BattleSpirit, eff_type: EffectType) -> int:
    """Return stack count for stack-based effects."""
    effect = next((e for e in spirit.effects if e.type == eff_type), None)
    return stack_count(effect) if effect else 0


def _stat_base(spirit: BattleSpirit, stat: StatType) -> int:
    base_stats = spirit.base_stats
    if stat == StatType.hp:
        return base_stats.hp
    if stat == StatType.atk:
        return base_stats.atk
    if stat == StatType.mag_atk:
        return base_stats.mag_atk
    if stat == StatType.def_:
        return base_stats.def_
    if stat == StatType.mag_def:
        return base_stats.mag_def
    if stat == StatType.speed:
        return base_stats.speed
    return 0


def _conversion_flat_bonus(
    spirit: BattleSpirit,
    stat: StatType,
    engine: Any,
) -> float:
    """转化类固定加成；计算底数始终排除转化（见 mechanics.md 第 8 节，不可二次转化）。

    - 攻击类（物攻/魔攻）：辣子鸡 / 水煮鱼。
    - 防御类（物防/魔防）：恶魔战士「肉盾」按己方存活“肉盾”携带者双防之和的比例，
      同时为全队（含自身）的物防与魔防各提供该固定加成。
    """
    bonus = 0.0
    if stat in (StatType.atk, StatType.mag_atk):
        for effect in spirit.effects:
            if effect.type != EffectType.buff_laziji or not effect.value:
                continue
            source = engine.find_spirit_anywhere(effect.source_id)
            if not source or not source.is_alive:
                continue
            base_atk = get_effective_stat(source, StatType.atk, exclude_conversion=True)
            bonus += base_atk * effect.value
        for ally in engine.get_all_spirits(spirit.owner_id):
            if not ally.is_alive:
                continue
            for effect in ally.effects:
                if effect.type != EffectType.buff_shuizhuyu or not effect.value:
                    continue
                base_atk = get_effective_stat(ally, StatType.atk, exclude_conversion=True)
                bonus += base_atk * effect.value
    elif stat in (StatType.def_, StatType.mag_def):
        for ally in engine.get_all_spirits(spirit.owner_id):
            if not ally.is_alive:
                continue
            for effect in ally.effects:
                if effect.type != EffectType.state_roudun or not effect.value:
                    continue
                base_def = get_effective_stat(ally, StatType.def_, exclude_conversion=True)
                base_mag_def = get_effective_stat(ally, StatType.mag_def, exclude_conversion=True)
                bonus += (base_def + base_mag_def) * effect.value
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
        elif effect.type == EffectType.debuff_stat_percent_reduction:
            percent_sum -= effect.value
        elif effect.type == EffectType.debuff_flaw and stat == StatType.def_:
            # 破绽：专用物防降低（当前为效果 value，如 4%），故意不走
            # debuff_stat_percent_reduction，避免被圣域祭司「再现」判定为可复制的能力值降低类效果。
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
    floor = base * 0.2
    return max(floor, result)


def get_effective_speed(spirit: BattleSpirit) -> float:
    return get_effective_stat(spirit, StatType.speed)
