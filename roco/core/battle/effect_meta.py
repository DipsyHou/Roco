"""Effect metadata and stack helpers.

语义约定：
- category：效果归属（正面 buff / 负面 debuff / 状态 state）。state 是 effect 的一种。
- uses_stacks：这个效果的 ``BattleEffect.stacks`` 有实际层数/计数字段意义。
- stackable：同类效果在状态栏是否按规则合并显示为一行；它不等于 uses_stacks。

不能叠层、也不使用层数的效果，``stacks`` 应为 ``None``。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from .enums import EffectType

EffectCategory = Literal["buff", "debuff", "state"]


@dataclass(frozen=True)
class EffectMeta:
    category: EffectCategory
    uses_stacks: bool = False
    stackable: bool = False
    max_stacks: Optional[int] = None


# 有“层数/计数”语义的效果。注意：有层数不一定代表需要把多条实例合并显示。
STACK_COUNT_EFFECT_TYPES: frozenset[EffectType] = frozenset(
    {
        EffectType.debuff_burn,
        EffectType.debuff_poison,
        EffectType.debuff_parasite,
        EffectType.debuff_freeze,
        EffectType.state_warmup,
        EffectType.state_shunt,
        EffectType.state_expansion,
        EffectType.state_lingqi,
        EffectType.state_gangqi,
        EffectType.state_quxie,
        EffectType.state_zhensha,
        EffectType.state_zhaojia,
        EffectType.state_jianwu,
        EffectType.state_huoli,
    }
)

# 状态栏需要合并成一行的“可叠加”效果。
STACKABLE_DISPLAY_EFFECT_TYPES: frozenset[EffectType] = frozenset(
    {
        EffectType.debuff_burn,
        EffectType.debuff_poison,
        EffectType.debuff_parasite,
        EffectType.debuff_freeze,
        EffectType.state_warmup,
        EffectType.state_gangqi,
        EffectType.state_quxie,
        EffectType.state_zhensha,
        EffectType.state_zhaojia,
        EffectType.state_jianwu,
        EffectType.state_huoli,
    }
)


def effect_category(effect_type: EffectType) -> EffectCategory:
    if effect_type.value.startswith("debuff_"):
        return "debuff"
    if effect_type.value.startswith("state_"):
        return "state"
    return "buff"


def effect_meta(effect_type: EffectType) -> EffectMeta:
    return EffectMeta(
        category=effect_category(effect_type),
        uses_stacks=effect_type in STACK_COUNT_EFFECT_TYPES,
        stackable=effect_type in STACKABLE_DISPLAY_EFFECT_TYPES,
    )


def uses_stacks(effect_type: EffectType) -> bool:
    return effect_type in STACK_COUNT_EFFECT_TYPES


def is_stackable_effect_type(effect_type: EffectType) -> bool:
    return effect_type in STACKABLE_DISPLAY_EFFECT_TYPES


def normalize_stacks(raw: object) -> int:
    return max(0, int(raw or 0))


def stack_count(effect: object) -> int:
    return normalize_stacks(getattr(effect, "stacks", None))
