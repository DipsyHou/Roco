"""护盾系统 — 见 docs/mechanics.md §22。

本模块只提供**与具体精灵无关**的护盾机制；各精灵如何获得 / 使用护盾由各自的
``SpiritLogic`` 决定。护盾以 ``BattleEffect(type=state_shield)`` 表示：

- ``value``：当前护盾量（整数）。
- ``source_id``：授予该护盾的来源精灵；**来源归并**的键。
- ``duration_turns``：持续回合；随 ``tick_effects`` 递减、到期移除。
- ``display_name``：状态栏展示名。

规则要点：

- **来源归并**：同一 ``source_id`` 的护盾合并为一条（累积、共享上限、刷新持续）；
  不同来源是各自独立的多条护盾，可并存。
- **并行抵扣**：受到一次伤害时，每条护盾各自扣除全额；
  掉血 = ``max(0, 伤害 - 抵扣前最厚的一条护盾)``。
- **上限（方案 B）**：仅在获得 / 累积时作为闸门，不回溯削减已有护盾量：
  ``新护盾量 = max(旧, min(旧 + 授予, 上限))``。授予量与上限均由调用方实时算好后传入。
"""

from __future__ import annotations

from typing import List, Optional

from .status_effects import make_effect
from .types import BattleEffect, BattleSpirit, EffectType

SHIELD_TYPE = EffectType.state_shield


def get_shields(spirit: BattleSpirit) -> List[BattleEffect]:
    """返回该精灵当前所有护盾量 > 0 的护盾效果。"""
    return [e for e in spirit.effects if e.type == SHIELD_TYPE and (e.value or 0) > 0]


def total_shield(spirit: BattleSpirit) -> int:
    """当前身上所有护盾量之和（供「自身护盾量」类结算使用）。"""
    return int(sum(int(e.value or 0) for e in get_shields(spirit)))


def max_shield(spirit: BattleSpirit) -> int:
    """当前身上最厚一条护盾的量（无护盾则为 0）。

    这也是面对单次伤害时的「有效护盾值」——并行抵扣下掉血 = 伤害 − 最厚一条盾。
    """
    shields = get_shields(spirit)
    return max((int(e.value or 0) for e in shields), default=0)


def shield_from_source(spirit: BattleSpirit, source_id: str) -> Optional[BattleEffect]:
    """返回由 ``source_id`` 提供的那一条护盾（若存在）。"""
    return next(
        (e for e in spirit.effects if e.type == SHIELD_TYPE and e.source_id == source_id),
        None,
    )


def has_shield_from(spirit: BattleSpirit, source_id: str) -> bool:
    """该精灵是否持有由 ``source_id`` 提供、且护盾量 > 0 的护盾。"""
    eff = shield_from_source(spirit, source_id)
    return eff is not None and (eff.value or 0) > 0


def grant_shield(
    target: BattleSpirit,
    source_id: str,
    amount: float,
    cap: float,
    *,
    duration: Optional[int],
    display_name: str = "护盾",
) -> int:
    """按方案 B 授予 / 累积护盾，返回实际增加的护盾量。

    ``新护盾量 = max(旧, min(旧 + amount, cap))``；来源相同则合并为一条并刷新持续时间。
    """
    amount = max(0, int(amount))
    cap = max(0, int(cap))
    existing = shield_from_source(target, source_id)
    if existing is not None:
        old = int(existing.value or 0)
        new = max(old, min(old + amount, cap))
        existing.value = new
        existing.duration_turns = duration
        if display_name:
            existing.display_name = display_name
        return new - old
    new = min(amount, cap)
    if new <= 0:
        return 0
    target.effects.append(
        make_effect(
            SHIELD_TYPE,
            source_id,
            duration_turns=duration,
            value=new,
            display_name=display_name,
        )
    )
    return new


def absorb(spirit: BattleSpirit, damage: int) -> int:
    """用护盾抵扣一次伤害，返回落到生命上的伤害；就地更新 / 移除护盾。

    并行抵扣：每条护盾各扣全额；掉血 = ``max(0, damage - 最厚一条盾)``。
    """
    if damage <= 0:
        return damage
    shields = get_shields(spirit)
    if not shields:
        return damage
    max_shield = max(int(e.value or 0) for e in shields)
    for e in shields:
        e.value = max(0, int(e.value or 0) - damage)
    spirit.effects = [
        e
        for e in spirit.effects
        if not (e.type == SHIELD_TYPE and (e.value or 0) <= 0)
    ]
    return max(0, damage - max_shield)
