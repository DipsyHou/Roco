"""Centralized battle-log message text (Chinese).

Keep all engine / pipeline / DoT log strings here so wording stays consistent
and is easy to audit. Status-bar / effect display text lives in
``effect_display.py``; this module is only for ``battle_log`` entries.
"""

from __future__ import annotations

BATTLE_START = "战斗开始！"
ACTION_EXCEPTION = "行动执行时发生了异常，已跳过。"


def battle_end(winner_id: str) -> str:
    return f"战斗结束！玩家 {winner_id} 获胜！"


def used_gather(name: str) -> str:
    return f"{name} 使用了聚能！"


def skipped_action(name: str) -> str:
    return f"{name} 跳过了行动。"


def used_skill(actor_name: str, skill_name: str) -> str:
    return f"{actor_name} 使用了 {skill_name}！"


def physical_hit(attacker_name: str, target_name: str, damage: int) -> str:
    return f"{attacker_name} 对 {target_name} 造成了 {damage} 点物理伤害！"


def defeated(name: str) -> str:
    return f"{name} 被击败了！"


def effect_expired(name: str) -> str:
    return f"{name} 的一个效果到期消失了。"


def team_energy_gain(player_id: str, gained: int, current: int, cap: int) -> str:
    return f"玩家 {player_id} 回复了 {gained} 点队伍能量（{current}/{cap}）"


def team_energy_reason(reason: str, current: int, cap: int) -> str:
    return f"{reason}（{current}/{cap}）"


def stunned_normal(name: str) -> str:
    return f"{name} 处于眩晕状态，跳过了本次行动！"


def stunned_extra(name: str) -> str:
    return f"{name} 处于眩晕状态，跳过了本次额外行动！"


# --- damage-over-time ---

def burn_tick(target_name: str, source_name: str, damage: int) -> str:
    return f"{target_name} 因 {source_name} 的灼烧受到 {damage} 点物理伤害！"


def burn_weakened(target_name: str) -> str:
    return f"{target_name} 的灼烧减弱了。"


def poison_tick(target_name: str, damage: int) -> str:
    return f"{target_name} 因中毒受到 {damage} 点固伤！"


def poison_cleared(target_name: str) -> str:
    return f"{target_name} 的中毒消失了。"


def freeze_execute(target_name: str) -> str:
    return f"{target_name} 因冰冻处决而阵亡！"
