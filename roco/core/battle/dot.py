"""Damage-over-time system effects."""

from __future__ import annotations

from typing import Any

from . import messages as msg
from .damage import calculate_damage
from .damage_segment import execute_damage_segment
from .effect_meta import stack_count
from .effects import get_burn_effects, get_parasite_effects, get_poison_effect
from .events import DamageSource
from .hp import execute_instant_defeat
from .stats import get_effective_stat
from .types import BattleLogType, BattleSpirit, DamageType, EffectType, StatType

PARASITE_MAG_RATIO = 0.04


def trigger_burn_damage(ctx: Any, target: BattleSpirit) -> None:
    """Resolve burn once per source; does not halve stacks (see 主动触发)."""
    if not target.is_alive:
        return
    for effect in list(get_burn_effects(target)):
        stacks = stack_count(effect)
        if stacks <= 0:
            target.effects = [e for e in target.effects if e.id != effect.id]
            continue

        source = ctx.find_spirit_anywhere(effect.source_id)
        if source and source.is_alive:
            atk = get_effective_stat(source, StatType.atk)
            raw = atk * 0.1 * stacks
            damage = calculate_damage(
                raw,
                DamageType.physical,
                source,
                target,
                sustained="burn",
            )
            if damage > 0:
                execute_damage_segment(
                    ctx,
                    source,
                    target,
                    damage,
                    source=DamageSource.dot,
                    describe=lambda actual: msg.burn_tick(target.name, source.name, actual),
                )
                if not target.is_alive:
                    return


def process_burn_on_action_end(ctx: Any, target: BattleSpirit) -> None:
    """Resolve burn damage, then halve stacks from each source."""
    trigger_burn_damage(ctx, target)
    if not target.is_alive:
        return
    for effect in list(get_burn_effects(target)):
        stacks = stack_count(effect)
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


def trigger_parasite_damage(ctx: Any, target: BattleSpirit) -> None:
    """Resolve parasite once per source; does not reduce stacks."""
    if not target.is_alive:
        return
    for effect in list(get_parasite_effects(target)):
        stacks = stack_count(effect)
        if stacks <= 0:
            target.effects = [e for e in target.effects if e.id != effect.id]
            continue

        source = ctx.find_spirit_anywhere(effect.source_id)
        if not source or not source.is_alive:
            continue

        mag = get_effective_stat(source, StatType.mag_atk)
        raw = mag * PARASITE_MAG_RATIO * stacks
        damage = calculate_damage(
            raw,
            DamageType.magical,
            source,
            target,
            sustained="parasite",
        )
        if damage <= 0:
            continue
        execute_damage_segment(
            ctx,
            source,
            target,
            damage,
            source=DamageSource.dot,
            describe=lambda actual, t=target.name, s=source.name: msg.parasite_tick(t, s, actual),
            lifesteal_ratio=1.0,
            lifesteal_healer=source,
        )
        if not target.is_alive:
            return


def process_parasite_on_action_end(ctx: Any, target: BattleSpirit) -> None:
    """Resolve parasite damage, then reduce stacks by 1 per source."""
    trigger_parasite_damage(ctx, target)
    if not target.is_alive:
        return
    for effect in list(get_parasite_effects(target)):
        stacks = stack_count(effect)
        if stacks <= 0:
            target.effects = [e for e in target.effects if e.id != effect.id]
            continue
        new_stacks = stacks - 1
        if new_stacks <= 0:
            target.effects = [e for e in target.effects if e.id != effect.id]
            ctx.add_log(
                BattleLogType.effect_removed,
                msg.parasite_cleared(target.name),
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
    """Resolve poison fixed damage via the shared segment pipeline (灵珏 / 深根)."""
    if not target.is_alive:
        return
    effect = get_poison_effect(target)
    if not effect or stack_count(effect) <= 0:
        if effect:
            target.effects = [e for e in target.effects if e.id != effect.id]
        return

    stacks = stack_count(effect)
    raw = target.max_hp * 0.01 * stacks
    damage = calculate_damage(
        raw,
        DamageType.fixed,
        None,
        target,
        sustained="poison",
    )
    if damage > 0:
        # 无发起者：attacker=None；走段分配以便深根分摊。
        execute_damage_segment(
            ctx,
            None,
            target,
            damage,
            source=DamageSource.dot,
            describe=lambda a, t=target.name: msg.poison_tick(t, a),
            log_extra={"effectType": EffectType.debuff_poison.value},
        )
        if not target.is_alive:
            return

    if decrease:
        effect.stacks = stack_count(effect) - 1
        if stack_count(effect) <= 0:
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
    process_parasite_on_action_end(ctx, target)
    if target.is_alive:
        process_burn_on_action_end(ctx, target)
    if target.is_alive:
        process_poison_on_action_end(ctx, target)
    if target.is_alive:
        process_freeze_on_action_end(ctx, target)
