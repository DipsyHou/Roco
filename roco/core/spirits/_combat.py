"""Shared spirit combat helpers.

Historically every spirit re-implemented the same target-selection and
damage-dealing boilerplate (crit roll → apply → damage log → notify → defeat
log), which drifted subtly across files. These helpers centralise the mechanics
and the log ``data`` key conventions while letting each caller keep its own
Chinese log wording via ``describe`` / ``log_message``.

Log ``data`` keys (hard convention):
- damage: ``attackerId`` / ``targetId`` / ``damage``
- heal: ``actorId`` / ``targetId`` / ``heal``
- effect: ``sourceId`` / ``targetId`` (+ ``stacks`` when applicable)
"""

from __future__ import annotations

from typing import Callable, List, Optional

from ..battle.crit import log_critical_hit
from ..battle.damage_segment import execute_damage_segment
from ..battle.events import DamageSource
from ..battle.types import BattleLogType, BattleSpirit, DamageType, StatType
from ..battle.utils import (
    apply_burn_stacks,
    apply_heal,
    apply_parasite_stacks,
    apply_poison_stacks,
    calculate_damage,
    get_effective_stat,
    get_poison_stacks,
    get_total_parasite_stacks,
    trigger_burn_damage,
    trigger_poison_damage,
)

DamageMessage = Callable[[int], str]


def grant_personal_energy(ctx, spirit: BattleSpirit, amount: int) -> int:
    """Grant ``spirit`` personal energy (秘能), applying teammates' amplifiers.

    Every ``get_ally_energy_gain_bonus`` on ``spirit``'s living teammates
    (including ``spirit`` itself) is queried and added on top of ``amount``
    before capping at ``max_energy``. This is the single entry point personal-
    energy spirits should call instead of writing ``spirit.energy += n``
    directly, so amplifiers like 圣域祭司的月盈 apply uniformly. Returns the
    actual amount gained (post-cap).
    """
    from ..spirits import get_spirit_logic

    if amount <= 0 or spirit.energy is None:
        return 0
    bonus = 0
    for ally in ctx.get_active_spirits(spirit.owner_id):
        logic = get_spirit_logic(ally.template_id)
        if logic:
            bonus += logic.get_ally_energy_gain_bonus(ctx, ally, spirit)
    cap = spirit.max_energy
    before = spirit.energy
    after = before + amount + bonus
    if cap is not None:
        after = min(cap, after)
    spirit.energy = after
    return after - before


def target_enemy(
    ctx,
    player_id: str,
    target_id: Optional[str],
) -> Optional[BattleSpirit]:
    """Resolve a live enemy: the requested target if valid, else the first alive foe."""
    opponent_id = ctx.get_opponent_id(player_id)
    target = ctx.find_spirit_anywhere(target_id or "")
    if target and target.is_alive and target.owner_id == opponent_id:
        return target
    enemies = ctx.get_active_spirits(opponent_id)
    return enemies[0] if enemies else None


def target_ally(
    ctx,
    player_id: str,
    target_id: Optional[str],
) -> Optional[BattleSpirit]:
    """Resolve a live ally: the requested target if valid, else the first alive ally."""
    target = ctx.find_spirit_anywhere(target_id or "")
    if target and target.is_alive and target.owner_id == player_id:
        return target
    allies = ctx.get_active_spirits(player_id)
    return allies[0] if allies else None


def deal_damage(
    ctx,
    actor: BattleSpirit,
    target: BattleSpirit,
    raw: float,
    damage_type: DamageType,
    describe: DamageMessage,
    *,
    source: DamageSource = DamageSource.attack,
    crit_rng=None,
    lifesteal_ratio: float = 0.0,
    lifesteal_healer: Optional[BattleSpirit] = None,
) -> int:
    """Run the shared damage pipeline; ``describe(actual)`` builds the damage log line."""
    if not target.is_alive:
        return 0
    crit_flag: List[bool] = []
    dmg = calculate_damage(
        raw,
        damage_type,
        actor,
        target,
        crit_flag=crit_flag,
        rng=crit_rng,
    )
    return execute_damage_segment(
        ctx,
        actor,
        target,
        dmg,
        source=source,
        describe=describe,
        log_crit=(lambda: log_critical_hit(ctx, actor, target)) if crit_flag else None,
        lifesteal_ratio=lifesteal_ratio,
        lifesteal_healer=lifesteal_healer,
    )


def deal_atk_ratio(
    ctx,
    actor: BattleSpirit,
    target: BattleSpirit,
    ratio: float,
    describe: DamageMessage,
    *,
    source: DamageSource = DamageSource.attack,
    crit_rng=None,
) -> int:
    """Physical damage equal to ``atk * ratio``."""
    atk = get_effective_stat(actor, StatType.atk)
    return deal_damage(
        ctx,
        actor,
        target,
        atk * ratio,
        DamageType.physical,
        describe,
        source=source,
        crit_rng=crit_rng,
    )


def deal_mag_ratio(
    ctx,
    actor: BattleSpirit,
    target: BattleSpirit,
    ratio: float,
    describe: DamageMessage,
    *,
    source: DamageSource = DamageSource.skill,
    crit_rng=None,
) -> int:
    """Magical damage equal to ``mag_atk * ratio``."""
    mag = get_effective_stat(actor, StatType.mag_atk)
    return deal_damage(
        ctx,
        actor,
        target,
        mag * ratio,
        DamageType.magical,
        describe,
        source=source,
        crit_rng=crit_rng,
    )


def deal_heal(
    ctx,
    actor: BattleSpirit,
    target: BattleSpirit,
    amount: float,
    describe: DamageMessage,
) -> int:
    """Heal ``target`` and log with the standard heal keys."""
    if not target.is_alive or amount <= 0:
        return 0
    actual = apply_heal(target, amount)
    if actual > 0:
        ctx.add_log(
            BattleLogType.heal_applied,
            describe(actual),
            {"actorId": actor.unique_id, "targetId": target.unique_id, "heal": actual},
        )
    return actual


def grant_burn(
    ctx,
    actor: BattleSpirit,
    target: BattleSpirit,
    stacks: int,
    *,
    log_message: Optional[str] = None,
) -> bool:
    """Apply burn stacks; if the target is also poisoned, trigger poison damage."""
    if stacks <= 0 or not target.is_alive:
        return False
    if not apply_burn_stacks(target, actor.unique_id, stacks):
        return False
    msg = log_message or f"{target.name} 获得 {stacks} 层灼烧！"
    ctx.add_log(
        BattleLogType.effect_applied,
        msg,
        {"targetId": target.unique_id, "sourceId": actor.unique_id, "stacks": stacks},
    )
    if target.is_alive and get_poison_stacks(target) > 0:
        trigger_poison_damage(ctx, target)
    return True


def grant_parasite(
    ctx,
    actor: BattleSpirit,
    target: BattleSpirit,
    stacks: int,
    *,
    log_message: Optional[str] = None,
) -> bool:
    """Apply parasite stacks per source."""
    if stacks <= 0 or not target.is_alive:
        return False
    if not apply_parasite_stacks(target, actor.unique_id, stacks):
        return False
    total = get_total_parasite_stacks(target)
    msg = log_message or f"{target.name} 获得 {stacks} 层寄生（当前 {total} 层）！"
    ctx.add_log(
        BattleLogType.effect_applied,
        msg,
        {"targetId": target.unique_id, "sourceId": actor.unique_id, "stacks": stacks},
    )
    return True


def grant_poison(
    ctx,
    actor: BattleSpirit,
    target: BattleSpirit,
    stacks: int,
    *,
    log_message: Optional[str] = None,
) -> bool:
    """Apply poison stacks; then trigger burn damage if any burn is present."""
    if stacks <= 0 or not target.is_alive:
        return False
    if not apply_poison_stacks(target, actor.unique_id, stacks):
        return False
    msg = log_message or (
        f"{target.name} 获得 {stacks} 层中毒（当前 {get_poison_stacks(target)} 层）！"
    )
    ctx.add_log(
        BattleLogType.effect_applied,
        msg,
        {"targetId": target.unique_id, "sourceId": actor.unique_id, "stacks": stacks},
    )
    if target.is_alive:
        trigger_burn_damage(ctx, target)
    return True
