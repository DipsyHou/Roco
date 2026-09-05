"""Damage segment pipeline: share → lifesteal → shield/HP → events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from .events import DamageSource
from .hp import apply_damage, apply_heal
from .types import BattleLogType, BattleSpirit

DamageMessage = Callable[[int], str]


@dataclass(frozen=True)
class DamageApplication:
    target: BattleSpirit
    segment_amount: int
    emit_damage_event: bool = True


def resolve_damage_applications(
    ctx,
    primary_target: BattleSpirit,
    segment_amount: int,
) -> List[DamageApplication]:
    """Split ``segment_amount`` across the primary target and damage-share observers."""
    from ..spirits import get_spirit_logic

    if segment_amount <= 0:
        return []

    share_entries: List[tuple[BattleSpirit, int]] = []
    total_share = 0
    for ally in ctx.get_all_spirits(primary_target.owner_id):
        if not ally.is_alive:
            continue
        logic = get_spirit_logic(ally.template_id)
        if logic is None:
            continue
        share = logic.get_damage_share_for_ally(ctx, ally, primary_target, segment_amount)
        if share > 0:
            share_entries.append((ally, share))
            total_share += share

    if total_share > segment_amount:
        total_share = segment_amount

    primary_amount = segment_amount - total_share
    apps: List[DamageApplication] = []
    if primary_amount > 0:
        apps.append(DamageApplication(primary_target, primary_amount, True))
    for recipient, amount in share_entries:
        if amount <= 0:
            continue
        apps.append(DamageApplication(recipient, amount, False))
    return apps


def apply_lifesteal_from_segment(
    ctx,
    healer: BattleSpirit,
    segment_amount: int,
    ratio: float,
    *,
    log_message: Optional[str] = None,
) -> int:
    """Heal ``healer`` from the pre-shield segment amount."""
    if ratio <= 0 or segment_amount <= 0 or not healer.is_alive:
        return 0
    heal = int(segment_amount * ratio + 1e-9)
    if heal <= 0:
        return 0
    actual = apply_heal(healer, heal)
    if actual > 0:
        from . import messages as battle_msg

        text = log_message or battle_msg.heal_self(healer.name, actual)
        ctx.add_log(
            BattleLogType.heal_applied,
            text,
            {"actorId": healer.unique_id, "targetId": healer.unique_id, "heal": actual},
        )
    return actual


def execute_damage_segment(
    ctx,
    attacker: Optional[BattleSpirit],
    primary_target: BattleSpirit,
    segment_amount: int,
    *,
    source: DamageSource = DamageSource.other,
    describe: Optional[DamageMessage] = None,
    critical: bool = False,
    log_crit: Optional[Callable[[], None]] = None,
    lifesteal_ratio: float = 0.0,
    lifesteal_healer: Optional[BattleSpirit] = None,
    lifesteal_log: Optional[str] = None,
    log_extra: Optional[dict] = None,
) -> int:
    """Apply one calculated damage segment to ``primary_target`` (and share recipients).

    ``critical`` folds the crit flag into the damage log (no separate crit line).
    ``log_crit`` is kept for backward compatibility but ignored when set — prefer
    ``critical=True``.
    """
    del log_crit  # merged into the damage entry via ``critical``
    if segment_amount <= 0 or not primary_target.is_alive:
        return 0

    applications = resolve_damage_applications(ctx, primary_target, segment_amount)
    if not applications:
        applications = [DamageApplication(primary_target, segment_amount, True)]

    primary_reported = 0
    applied: List[tuple[DamageApplication, int]] = []
    for app in applications:
        if not app.target.is_alive or app.segment_amount <= 0:
            continue
        reported = apply_damage(app.target, app.segment_amount, ctx=ctx)
        applied.append((app, reported))
        if app.target.unique_id == primary_target.unique_id:
            primary_reported = reported

    if describe is not None and primary_reported > 0:
        from . import messages as battle_msg

        text = describe(primary_reported)
        if critical:
            text = battle_msg.mark_critical(text)
        data = {
            "attackerId": attacker.unique_id if attacker else None,
            "targetId": primary_target.unique_id,
            "damage": primary_reported,
        }
        if critical:
            data["critical"] = True
        if log_extra:
            data.update(log_extra)
        ctx.add_log(
            BattleLogType.damage_dealt,
            text,
            data,
        )

    for app, reported in applied:
        if app.emit_damage_event and reported > 0:
            ctx.notify_damage_taken(attacker, app.target, reported, source=source)
        if not app.target.is_alive:
            from . import messages as battle_msg

            ctx.add_log(
                BattleLogType.spirit_defeated,
                battle_msg.defeated(app.target.name),
                {"targetId": app.target.unique_id},
            )

    healer = lifesteal_healer if lifesteal_healer is not None else attacker
    if lifesteal_ratio > 0 and healer is not None:
        apply_lifesteal_from_segment(
            ctx,
            healer,
            segment_amount,
            lifesteal_ratio,
            log_message=lifesteal_log,
        )

    return primary_reported
