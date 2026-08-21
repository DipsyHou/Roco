"""Critical-hit mechanics.

暴击是 battle 层的通用机制：本模块集中负责暴击属性读取、掷点、基础伤害
放大，以及统一战斗日志。精灵逻辑只需要通过 effect / hook 提供暴击率和
暴击效果，不应该自己生成暴击日志。
"""

from __future__ import annotations

import random as _random
from typing import Optional, Tuple

from .types import BattleLogType, BattleSpirit, EffectType

DEFAULT_CRIT_DAMAGE_PERCENT = 100.0


def get_crit_stats(
    attacker: BattleSpirit, target: Optional[BattleSpirit] = None
) -> Tuple[float, float]:
    """Return ``(crit_rate, crit_damage_percent)`` for one damage segment.

    ``crit_rate`` is clamped to 0~1. ``crit_damage_percent`` uses 100 as the
    no-bonus baseline, so +60% crit damage is represented as 160.
    """
    from ..spirits import get_spirit_logic

    crit_rate = 0.0
    crit_damage_percent = DEFAULT_CRIT_DAMAGE_PERCENT

    for effect in attacker.effects:
        if effect.value is None:
            continue
        if effect.type == EffectType.buff_crit_rate:
            crit_rate += effect.value
        elif effect.type == EffectType.buff_crit_damage:
            crit_damage_percent += effect.value

    logic = get_spirit_logic(attacker.template_id)
    if logic:
        crit_rate += logic.get_crit_rate_bonus(attacker, target)
        crit_damage_percent += logic.get_crit_damage_bonus(attacker, target)

    crit_rate = min(1.0, max(0.0, crit_rate))
    crit_damage_percent = max(0.0, crit_damage_percent)
    return crit_rate, crit_damage_percent


def apply_crit_to_base(
    base: float,
    attacker: BattleSpirit,
    *,
    target: Optional[BattleSpirit] = None,
    crit_flag: Optional[list[bool]] = None,
    rng: Optional[object] = None,
) -> Tuple[float, bool]:
    """Apply crit to pre-modifier base damage and return ``(damage, was_crit)``.

    All non-zero damage segments pass through this function. A 0% crit rate
    skips RNG to keep deterministic RNG counters stable.
    """
    if base <= 0:
        return base, False
    crit_rate, crit_damage_percent = get_crit_stats(attacker, target)
    if crit_rate <= 0:
        return base, False
    roll = rng.random() if rng is not None else _random.random()
    if roll < crit_rate:
        if crit_flag is not None:
            crit_flag.append(True)
        return base * (crit_damage_percent / 100.0), True
    return base, False


def log_critical_hit(ctx, attacker: BattleSpirit, target: BattleSpirit) -> None:
    """Append the standard critical-hit log entry."""
    ctx.add_log(
        BattleLogType.damage_dealt,
        f"暴击！{attacker.name} 对 {target.name} 的伤害触发了暴击！",
        {
            "attackerId": attacker.unique_id,
            "targetId": target.unique_id,
            "critical": True,
        },
    )


# Backward-compatible private alias for older imports/tests during transition.
_apply_crit_to_base = apply_crit_to_base
