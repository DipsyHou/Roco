"""Centralized battle-log Chinese copy and shared ``data`` helpers.

All ``battle_log`` entry text should use these templates (engine + spirits).
Status-bar / effect display strings stay in ``effect_display.py``.

Templates (no spirit-specific copy):
- Damage: ``damage`` / ``skill_damage`` / ``physical_hit`` / ``magical_hit`` / ``fixed_hit``
- Heal: ``heal`` / ``heal_self``
- HP cost: ``hp_cost``
- Defeat: ``defeated``
- Effect: ``effect_gained`` / ``effect_gained_from`` / ``effect_lost`` / ``effect_cleared``
- Stacks: ``gained_stacks`` (also via ``effect_gained(..., stacks=)``)
- Passive: ``passive`` — name only; follow with heal/effect logs if needed
- Purge: ``purged_*``
- Shield: ``shield_gain``
- Misc: ``extra_action`` / ``turn_advanced`` / ``replicate_*`` / card ops

Log ``data`` keys:
- damage: ``attackerId`` / ``targetId`` / ``damage`` (+ ``critical``)
- heal: ``actorId`` / ``targetId`` / ``heal``
- effect: ``sourceId`` / ``targetId`` (+ ``stacks`` when applicable)
- HP cost: ``damage_dealt`` with self ids + ``damage``
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BATTLE_START = "战斗开始！"
ACTION_EXCEPTION = "行动执行时发生了异常，已跳过。"

KIND_PHYSICAL = "物理"
KIND_MAGICAL = "魔法"
KIND_FIXED = "固定"


# ---------------------------------------------------------------------------
# data helpers
# ---------------------------------------------------------------------------

def data_damage(
    attacker_id: Optional[str],
    target_id: str,
    damage: int,
    **extra: Any,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "attackerId": attacker_id,
        "targetId": target_id,
        "damage": int(damage),
    }
    payload.update(extra)
    return payload


def data_heal(
    actor_id: str,
    target_id: str,
    heal: int,
    **extra: Any,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "actorId": actor_id,
        "targetId": target_id,
        "heal": int(heal),
    }
    payload.update(extra)
    return payload


def data_effect(
    target_id: str,
    source_id: Optional[str] = None,
    **extra: Any,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"targetId": target_id}
    if source_id is not None:
        payload["sourceId"] = source_id
    payload.update(extra)
    return payload


def data_hp_cost(spirit_id: str, damage: int, **extra: Any) -> Dict[str, Any]:
    """Self HP spend logged as ``damage_dealt`` (floats as damage on self)."""
    return data_damage(spirit_id, spirit_id, damage, **extra)


# ---------------------------------------------------------------------------
# Engine / pipeline
# ---------------------------------------------------------------------------

def battle_end(winner_id: str) -> str:
    return f"战斗结束！玩家 {winner_id} 获胜！"


def used_gather(name: str) -> str:
    return f"{name} 使用了聚能！"


def skipped_action(name: str) -> str:
    return f"{name} 跳过了行动。"


def used_skill(actor_name: str, skill_name: str) -> str:
    return f"{actor_name} 使用了 {skill_name}！"


def stunned_normal(name: str) -> str:
    return f"{name} 处于眩晕状态，跳过了本次行动！"


def stunned_extra(name: str) -> str:
    return f"{name} 处于眩晕状态，跳过了本次额外行动！"


def effect_expired(name: str) -> str:
    return f"{name} 的一个效果到期消失了。"


def team_energy_gain(player_id: str, gained: int, current: int, cap: int) -> str:
    return f"玩家 {player_id} 回复了 {gained} 点队伍能量（{current}/{cap}）"


def team_energy_reason(reason: str, current: int, cap: int) -> str:
    return f"{reason}（{current}/{cap}）"


# ---------------------------------------------------------------------------
# Shared combat formats
# ---------------------------------------------------------------------------

def damage(
    attacker: str,
    target: str,
    amount: int,
    *,
    kind: str = KIND_PHYSICAL,
    skill: Optional[str] = None,
    critical: bool = False,
) -> str:
    if skill:
        text = f"{attacker} 的{skill}对 {target} 造成了 {amount} 点{kind}伤害！"
    else:
        text = f"{attacker} 对 {target} 造成了 {amount} 点{kind}伤害！"
    return mark_critical(text) if critical else text


def mark_critical(message: str) -> str:
    """Prefix a damage line with 暴击！ (idempotent)."""
    if message.startswith("暴击！"):
        return message
    return f"暴击！{message}"


def physical_hit(
    attacker_name: str,
    target_name: str,
    amount: int,
    *,
    critical: bool = False,
) -> str:
    return damage(
        attacker_name,
        target_name,
        amount,
        kind=KIND_PHYSICAL,
        critical=critical,
    )


def magical_hit(
    attacker_name: str,
    target_name: str,
    amount: int,
    *,
    critical: bool = False,
) -> str:
    return damage(
        attacker_name,
        target_name,
        amount,
        kind=KIND_MAGICAL,
        critical=critical,
    )


def fixed_hit(
    attacker_name: str,
    target_name: str,
    amount: int,
    *,
    critical: bool = False,
) -> str:
    return damage(
        attacker_name,
        target_name,
        amount,
        kind=KIND_FIXED,
        critical=critical,
    )


def skill_damage(
    attacker: str,
    skill: str,
    target: str,
    amount: int,
    *,
    kind: str = KIND_PHYSICAL,
    critical: bool = False,
) -> str:
    return damage(
        attacker, target, amount, kind=kind, skill=skill, critical=critical
    )


def heal(actor: str, target: str, amount: int, *, skill: Optional[str] = None) -> str:
    if actor == target:
        return heal_self(actor, amount, skill=skill)
    if skill:
        return f"{actor} 的{skill}为 {target} 回复了 {amount} 点生命！"
    return f"{actor} 为 {target} 回复了 {amount} 点生命！"


def heal_self(actor: str, amount: int, *, skill: Optional[str] = None) -> str:
    if skill:
        return f"{actor} 的{skill}回复了 {amount} 点生命！"
    return f"{actor} 回复了 {amount} 点生命！"


def critical_hit(attacker: str, target: str) -> str:
    """Deprecated standalone crit line; prefer ``damage(..., critical=True)``."""
    return f"暴击！{attacker} 对 {target} 触发了暴击！"


def hp_cost(name: str, amount: int, *, skill: Optional[str] = None) -> str:
    if skill:
        return f"{name} 为{skill}消耗了 {amount} 点生命！"
    return f"{name} 消耗了 {amount} 点生命！"


def defeated(name: str) -> str:
    return f"{name} 被击败了！"


def effect_gained(
    target: str,
    name: str,
    *,
    stacks: Optional[int] = None,
    total: Optional[int] = None,
) -> str:
    """Name-only buff/debuff gain (optional stack count for DoTs)."""
    if stacks is not None:
        return gained_stacks(target, stacks, name, total=total)
    return f"{target} 获得了 {name}！"


def effect_gained_from(
    source: str,
    target: str,
    name: str,
    *,
    stacks: Optional[int] = None,
) -> str:
    if stacks is not None:
        return f"{source} 使 {target} 获得了 {stacks} 层{name}！"
    return f"{source} 使 {target} 获得了 {name}！"


def effect_lost(target: str, name: str) -> str:
    return f"{target} 的{name}消失了！"


def effect_cleared(target: str, name: str) -> str:
    return f"{target} 的{name}被清除了！"


def passive(name: str, passive_name: str) -> str:
    """Passive trigger line — detail belongs in a following heal/effect log."""
    return f"{name} 的{passive_name}触发！"


def gained_stacks(
    target: str,
    stacks: int,
    effect_name: str,
    *,
    total: Optional[int] = None,
) -> str:
    if total is not None:
        return f"{target} 获得了 {stacks} 层{effect_name}（当前 {total} 层）！"
    return f"{target} 获得了 {stacks} 层{effect_name}！"


def purged_debuffs(target: str, count: Optional[int] = None) -> str:
    if count is None:
        return f"{target} 的负面效果被净化了！"
    return f"{target} 的 {count} 个负面效果被净化了！"


def purged_one_debuff(target: str) -> str:
    return f"{target} 的一个负面效果被解除了！"


def purged_buffs(target: str, count: int, *, source: Optional[str] = None) -> str:
    if source:
        return f"{source} 使 {target} 的 {count} 个正面效果被清除了！"
    return f"{target} 的 {count} 个正面效果被清除了！"


def purged_one_buff(target: str) -> str:
    return f"{target} 的一个正面效果被驱散了！"


def shield_gain(target: str, name: str = "护盾", *, source: Optional[str] = None) -> str:
    """Shield apply — name only (amount belongs in ``data`` if needed)."""
    if source:
        return effect_gained_from(source, target, name)
    return effect_gained(target, name)


def extra_action(source: str, targets: str) -> str:
    return f"{source} 使 {targets} 立刻获得了一次额外行动！"


def turn_advanced(source: str, target: str) -> str:
    return f"{source} 使 {target} 下一回合提前了100%！"


def replicate_empty(source: str, target: str) -> str:
    return f"{source} 对 {target} 施放了再现，但没有可复制的负面效果！"


def replicate_to_enemies(source: str, target: str) -> str:
    return f"{source} 的再现将 {target} 的一个负面效果复制给了敌方全体！"


def effect_blocked(name: str) -> str:
    return f"{name}效果已生效，无法叠加！"


def drew_card(name: str, card: str) -> str:
    return f"{name} 抽取了 {card}！"


def discarded_card(name: str, card: str) -> str:
    return f"{name} 弃置了 {card}！"


def played_card(name: str, card: str) -> str:
    return f"{name} 打出了 {card}！"


def consumed_card(name: str, card: str) -> str:
    return f"{name} 消耗了 {card}！"


def transformed_card(name: str, old: str, new: str) -> str:
    return f"{name} 将 {old} 变为了 {new}！"


# ---------------------------------------------------------------------------
# DoT / freeze
# ---------------------------------------------------------------------------

def burn_tick(target_name: str, source_name: str, damage: int) -> str:
    return f"{target_name} 因 {source_name} 的灼烧受到 {damage} 点物理伤害！"


def burn_weakened(target_name: str) -> str:
    return f"{target_name} 的灼烧减弱了。"


def poison_tick(target_name: str, damage: int) -> str:
    return f"{target_name} 因中毒受到 {damage} 点固伤！"


def poison_cleared(target_name: str) -> str:
    return f"{target_name} 的中毒消失了。"


def parasite_tick(target_name: str, source_name: str, damage: int) -> str:
    return f"{target_name} 因 {source_name} 的寄生受到 {damage} 点魔法伤害！"


def parasite_lifesteal(source_name: str, heal: int) -> str:
    return heal_self(source_name, heal, skill="寄生")


def parasite_cleared(target_name: str) -> str:
    return f"{target_name} 的寄生消失了。"


def freeze_execute(target_name: str) -> str:
    return f"{target_name} 被冻结。"
