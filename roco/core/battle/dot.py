"""Damage-over-time system effects."""

from __future__ import annotations

from typing import Any

from . import messages as msg
from .damage import calculate_damage
from .effects import get_burn_effects, get_poison_effect
from .hp import apply_damage, execute_instant_defeat
from .stats import get_effective_stat
from .types import BattleLogType, BattleSpirit, DamageType, EffectType, StatType


def get_sustained_damage_taken_amp(target: BattleSpirit) -> float:
    """Extra multiplier on burn/poison from effects tagged ``sustained_damage``."""
    total = 0.0
    for effect in target.effects:
        if (
            effect.type == EffectType.debuff_taken_damage_percent_boost
            and effect.effect_tag == "sustained_damage"
            and effect.value
        ):
            total += effect.value
    return total


def _apply_sustained_amp(target: BattleSpirit, damage: int) -> int:
    amp = get_sustained_damage_taken_amp(target)
    if amp <= 0 or damage <= 0:
        return damage
    return max(0, int(damage * (1 + amp) + 1e-9))


def trigger_burn_damage(ctx: Any, target: BattleSpirit) -> None:
    """Resolve burn once per source; does not halve stacks (see 主动触发)."""
    if not target.is_alive:
        return
    for effect in list(get_burn_effects(target)):
        stacks = effect.stacks
        if stacks <= 0:
            target.effects = [e for e in target.effects if e.id != effect.id]
            continue

        source = ctx.find_spirit_anywhere(effect.source_id)
        if source and source.is_alive:
            atk = get_effective_stat(source, StatType.atk)
            raw = atk * 0.1 * stacks
            damage = _apply_sustained_amp(
                target, calculate_damage(raw, DamageType.physical, source, target)
            )
            if damage > 0:
                actual = apply_damage(target, damage, ctx=ctx)
                if hasattr(ctx, "notify_damage_taken"):
                    ctx.notify_damage_taken(source, target, actual)
                ctx.add_log(
                    BattleLogType.damage_dealt,
                    msg.burn_tick(target.name, source.name, actual),
                    {
                        "attackerId": source.unique_id,
                        "targetId": target.unique_id,
                        "damage": actual,
                        "effectType": EffectType.debuff_burn.value,
                    },
                )
                if not target.is_alive:
                    ctx.add_log(
                        BattleLogType.spirit_defeated,
                        msg.defeated(target.name),
                        {"targetId": target.unique_id},
                    )
                    return


def process_burn_on_action_end(ctx: Any, target: BattleSpirit) -> None:
    """Resolve burn damage, then halve stacks from each source."""
    trigger_burn_damage(ctx, target)
    if not target.is_alive:
        return
    for effect in list(get_burn_effects(target)):
        stacks = effect.stacks
        if stacks <= 0:
            target.effects = [e for e in target.effects if e.id != effect.id]
            continue
        new_stacks = stacks // 2
        if new_stacks <= 0:
            target.effects = [e for e in target.effects if e.id != effect.id]
            ctx.add_log(
                BattleLogType.effect_removed,
                msg.burn_weakened(target.name),
                {"targetId": target.unique_id, "effectId": effect.id},
            )
        else:
            effect.stacks = new_stacks


def process_poison_damage(
    ctx: Any,
    target: BattleSpirit,
    *,
    decrease: bool = False,
) -> None:
    """Resolve poison fixed damage, optionally reducing stacks."""
    if not target.is_alive:
        return
    effect = get_poison_effect(target)
    if not effect or effect.stacks <= 0:
        if effect:
            target.effects = [e for e in target.effects if e.id != effect.id]
        return

    stacks = effect.stacks
    source = ctx.find_spirit_anywhere(effect.source_id)
    attacker = source if source else target
    raw = target.max_hp * 0.01 * stacks
    damage = _apply_sustained_amp(
        target, calculate_damage(raw, DamageType.fixed, attacker, target)
    )
    if damage > 0:
        actual = apply_damage(target, damage, ctx=ctx)
        if hasattr(ctx, "notify_damage_taken"):
            ctx.notify_damage_taken(attacker, target, actual)
        ctx.add_log(
            BattleLogType.damage_dealt,
            msg.poison_tick(target.name, actual),
            {
                "attackerId": getattr(attacker, "unique_id", None),
                "targetId": target.unique_id,
                "damage": actual,
                "effectType": EffectType.debuff_poison.value,
            },
        )
        if not target.is_alive:
            ctx.add_log(
                BattleLogType.spirit_defeated,
                msg.defeated(target.name),
                {"targetId": target.unique_id},
            )
            return

    if decrease:
        effect.stacks -= 1
        if effect.stacks <= 0:
            target.effects = [e for e in target.effects if e.id != effect.id]
            ctx.add_log(
                BattleLogType.effect_removed,
                msg.poison_cleared(target.name),
                {"targetId": target.unique_id, "effectId": effect.id},
            )


def trigger_poison_damage(ctx: Any, target: BattleSpirit) -> None:
    """Resolve poison once; does not reduce stacks."""
    process_poison_damage(ctx, target, decrease=False)


def process_poison_on_action_end(ctx: Any, target: BattleSpirit) -> None:
    process_poison_damage(ctx, target, decrease=True)


def process_freeze_on_action_end(ctx: Any, target: BattleSpirit) -> None:
    """Execute if HP is at or below 1% max HP per freeze stack (回合结束)."""
    if not target.is_alive:
        return
    from .effects import get_freeze_stacks

    stacks = get_freeze_stacks(target)
    if stacks <= 0:
        return
    threshold = target.max_hp * 0.01 * stacks
    if target.current_hp <= threshold:
        execute_instant_defeat(
            target,
            ctx=ctx,
            log_message=msg.freeze_execute(target.name),
        )


def process_system_effects_on_action_end(ctx: Any, target: BattleSpirit) -> None:
    """Resolve system effects at action end."""
    process_burn_on_action_end(ctx, target)
    if target.is_alive:
        process_poison_on_action_end(ctx, target)
    if target.is_alive:
        process_freeze_on_action_end(ctx, target)
