"""藤椒小巴 dish effect helpers."""

from __future__ import annotations

from typing import Optional

from ..battle.types import BattleEffect, BattleSpirit, EffectType
from ..battle.utils import make_effect

LAZIJI_RATIO = 0.10
LAZIJI_DURATION = 3
SHUIZHUYU_RATIO = 0.10
SHUIZHUYU_DURATION = 2
MAOXUEWANG_AMP = 0.15
MAOXUEWANG_DURATION = 3
OIL_ATK_BONUS = 0.20
OIL_DURATION = 3
OIL_HUOLI = 5
HUOLI_PER_BURN = 3
DISH_TAG_PREFIX = "dish:"
SUSTAINED_TAG = "sustained_damage"


def refresh_or_apply(
    target: BattleSpirit,
    *,
    eff_type: EffectType,
    source_id: str,
    duration: int,
    value: Optional[float] = None,
    display_name: Optional[str] = None,
    effect_tag: Optional[str] = None,
) -> None:
    existing = next((e for e in target.effects if e.type == eff_type), None)
    if existing and existing.source_id == source_id:
        existing.duration_turns = duration
        if value is not None:
            existing.value = value
        if effect_tag is not None:
            existing.effect_tag = effect_tag
        if display_name is not None:
            existing.display_name = display_name
        return
    if existing:
        target.effects = [e for e in target.effects if e is not existing]
    target.effects.append(
        make_effect(
            eff_type,
            source_id,
            duration_turns=duration,
            value=value,
            display_name=display_name,
            effect_tag=effect_tag,
        )
    )


def refresh_maoxuewang(target: BattleSpirit, source_id: str) -> None:
    existing = next(
        (
            e
            for e in target.effects
            if e.type == EffectType.debuff_taken_damage_percent_boost
            and e.display_name == "毛血旺"
        ),
        None,
    )
    if existing:
        existing.duration_turns = MAOXUEWANG_DURATION
        existing.value = MAOXUEWANG_AMP
        existing.source_id = source_id
        existing.effect_tag = SUSTAINED_TAG
        return
    target.effects.append(
        make_effect(
            EffectType.debuff_taken_damage_percent_boost,
            source_id,
            duration_turns=MAOXUEWANG_DURATION,
            value=MAOXUEWANG_AMP,
            display_name="毛血旺",
            effect_tag=SUSTAINED_TAG,
        )
    )


def dish_cap(effect: BattleEffect) -> Optional[int]:
    if (
        effect.type == EffectType.debuff_taken_damage_percent_boost
        and effect.display_name == "毛血旺"
    ):
        return MAOXUEWANG_DURATION
    tag = effect.effect_tag or ""
    if not tag.startswith(DISH_TAG_PREFIX):
        return None
    try:
        return int(tag[len(DISH_TAG_PREFIX) :])
    except ValueError:
        return None
