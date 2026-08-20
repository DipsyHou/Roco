"""Status-effect helpers for battle state effects and stacks."""

from __future__ import annotations

import random
import uuid
from typing import List, Optional

from .stats import is_buff_effect, is_debuff_effect
from .types import BattleEffect, BattleSpirit, DamageType, EffectType, StatType

SKILL_ENERGY_COST_ALL = "*"


def make_effect(
    eff_type: EffectType,
    source_id: str,
    *,
    duration_turns: Optional[int] = None,
    stacks: int = 0,
    stat_type: Optional[StatType] = None,
    value: Optional[float] = None,
    damage_type: Optional[DamageType] = None,
    channel_phase: Optional[int] = None,
    channel_skill_id: Optional[str] = None,
    effect_tag: Optional[str] = None,
    display_name: Optional[str] = None,
) -> BattleEffect:
    return BattleEffect(
        id=str(uuid.uuid4()),
        type=eff_type,
        source_id=source_id,
        duration_turns=duration_turns,
        stacks=stacks,
        stat_type=stat_type,
        value=value,
        damage_type=damage_type,
        channel_phase=channel_phase,
        channel_skill_id=channel_skill_id,
        effect_tag=effect_tag,
        display_name=display_name,
    )


def is_stunned(spirit: BattleSpirit) -> bool:
    return any(effect.type == EffectType.debuff_stun for effect in spirit.effects)



def is_action_blocked(spirit: BattleSpirit) -> bool:
    """Return whether generic control effects prevent action execution."""
    return is_stunned(spirit)



def is_debuff_immune(spirit: BattleSpirit) -> bool:
    return any(effect.type == EffectType.buff_debuff_immunity for effect in spirit.effects)



def has_infusion(spirit: BattleSpirit) -> bool:
    return any(effect.type == EffectType.buff_infusion for effect in spirit.effects)



def apply_infusion(
    spirit: BattleSpirit,
    source_id: str,
    *,
    duration_turns: int = 1,
) -> None:
    existing = next(
        (effect for effect in spirit.effects if effect.type == EffectType.buff_infusion),
        None,
    )
    if existing:
        existing.duration_turns = duration_turns
        existing.source_id = source_id
    else:
        spirit.effects.append(
            make_effect(
                EffectType.buff_infusion,
                source_id,
                duration_turns=duration_turns,
                display_name="浸润",
            )
        )



def purge_random_buff(
    spirit: BattleSpirit,
    rng: Optional[random.Random] = None,
) -> Optional[BattleEffect]:
    buffs = [effect for effect in spirit.effects if is_buff_effect(effect.type)]
    if not buffs:
        return None
    removed = (rng or random).choice(buffs)
    spirit.effects = [effect for effect in spirit.effects if effect.id != removed.id]
    return removed



def purge_random_buffs(
    spirit: BattleSpirit,
    count: int,
    rng: Optional[random.Random] = None,
) -> List[BattleEffect]:
    removed: List[BattleEffect] = []
    for _ in range(max(0, count)):
        buff = purge_random_buff(spirit, rng)
        if buff is None:
            break
        removed.append(buff)
    return removed



def count_buff_effects(spirit: BattleSpirit) -> int:
    return sum(1 for effect in spirit.effects if is_buff_effect(effect.type))



def get_skill_energy_cost_adjustments(
    spirit: BattleSpirit,
    skill_id: str,
) -> tuple[int, int]:
    """Return (increase, reduction) from battle effects for one skill."""
    increase = 0
    reduction = 0
    for effect in spirit.effects:
        if effect.type == EffectType.debuff_skill_energy_cost_increase:
            tag = effect.effect_tag
            if tag is None or tag == SKILL_ENERGY_COST_ALL or tag == skill_id:
                increase += int(effect.value or 0)
        elif effect.type == EffectType.buff_skill_energy_cost_reduction:
            if effect.effect_tag == skill_id:
                reduction += int(effect.value or 0)
    return increase, reduction



def adjust_skill_energy_cost(
    spirit: BattleSpirit,
    skill_id: str,
    base_cost: int,
) -> int:
    increase, reduction = get_skill_energy_cost_adjustments(spirit, skill_id)
    return max(0, base_cost + increase - reduction)



def apply_skill_energy_cost_increase(
    target: BattleSpirit,
    source_id: str,
    *,
    increase: int = 1,
    duration_turns: int = 3,
    effect_tag: str = SKILL_ENERGY_COST_ALL,
    display_name: Optional[str] = None,
) -> bool:
    if increase <= 0 or is_debuff_immune(target):
        return False
    existing = next(
        (
            effect
            for effect in target.effects
            if effect.type == EffectType.debuff_skill_energy_cost_increase
            and effect.effect_tag == effect_tag
        ),
        None,
    )
    if existing:
        existing.duration_turns = duration_turns
        existing.value = increase
        existing.source_id = source_id
        if display_name:
            existing.display_name = display_name
    else:
        target.effects.append(
            make_effect(
                EffectType.debuff_skill_energy_cost_increase,
                source_id,
                duration_turns=duration_turns,
                value=increase,
                effect_tag=effect_tag,
                display_name=display_name,
            )
        )
    return True



def purge_debuffs(spirit: BattleSpirit) -> List[BattleEffect]:
    removed = [effect for effect in spirit.effects if is_debuff_effect(effect.type)]
    spirit.effects = [effect for effect in spirit.effects if not is_debuff_effect(effect.type)]
    return removed



def get_warmup_effect(spirit: BattleSpirit) -> Optional[BattleEffect]:
    for effect in spirit.effects:
        if effect.type == EffectType.state_warmup:
            return effect
    return None



def get_warmup_stacks(spirit: BattleSpirit) -> int:
    effect = get_warmup_effect(spirit)
    return effect.stacks if effect else 0



def add_warmup_stacks(spirit: BattleSpirit, source_id: str, stacks: int) -> None:
    if stacks <= 0:
        return
    effect = get_warmup_effect(spirit)
    if effect:
        effect.stacks += stacks
    else:
        spirit.effects.append(
            make_effect(
                EffectType.state_warmup,
                source_id,
                stacks=stacks,
            )
        )



def tick_warmup_stacks(spirit: BattleSpirit, amount: int = 1) -> None:
    effect = get_warmup_effect(spirit)
    if not effect:
        return
    effect.stacks = max(0, effect.stacks - amount)
    if effect.stacks <= 0:
        spirit.effects = [e for e in spirit.effects if e.type != EffectType.state_warmup]



def get_burn_effects(spirit: BattleSpirit) -> List[BattleEffect]:
    return [effect for effect in spirit.effects if effect.type == EffectType.debuff_burn]



def get_total_burn_stacks(spirit: BattleSpirit) -> int:
    return sum(effect.stacks for effect in get_burn_effects(spirit))



def apply_burn_stacks(
    target: BattleSpirit,
    source_id: str,
    stacks: int,
) -> bool:
    if stacks <= 0 or is_debuff_immune(target):
        return False
    existing = next(
        (
            effect
            for effect in target.effects
            if effect.type == EffectType.debuff_burn and effect.source_id == source_id
        ),
        None,
    )
    if existing:
        existing.stacks += stacks
    else:
        target.effects.append(
            make_effect(EffectType.debuff_burn, source_id, stacks=stacks)
        )
    return True



def get_poison_effect(spirit: BattleSpirit) -> Optional[BattleEffect]:
    return next(
        (effect for effect in spirit.effects if effect.type == EffectType.debuff_poison),
        None,
    )



def get_poison_stacks(spirit: BattleSpirit) -> int:
    effect = get_poison_effect(spirit)
    return max(0, effect.stacks) if effect else 0



def apply_poison_stacks(
    target: BattleSpirit,
    source_id: str,
    stacks: int,
) -> bool:
    if stacks <= 0 or is_debuff_immune(target):
        return False
    existing = get_poison_effect(target)
    if existing:
        existing.stacks += stacks
    else:
        target.effects.append(
            make_effect(EffectType.debuff_poison, source_id, stacks=stacks)
        )
    return True



def get_freeze_effect(spirit: BattleSpirit) -> Optional[BattleEffect]:
    return next(
        (effect for effect in spirit.effects if effect.type == EffectType.debuff_freeze),
        None,
    )



def get_freeze_stacks(spirit: BattleSpirit) -> int:
    effect = get_freeze_effect(spirit)
    return max(0, effect.stacks) if effect else 0



def apply_freeze_stacks(
    target: BattleSpirit,
    source_id: str,
    stacks: int,
) -> bool:
    if stacks <= 0 or is_debuff_immune(target):
        return False
    existing = get_freeze_effect(target)
    if existing:
        existing.stacks += stacks
        existing.source_id = source_id
    else:
        target.effects.append(
            make_effect(EffectType.debuff_freeze, source_id, stacks=stacks)
        )
    return True



def tick_effects(
    spirit: BattleSpirit,
    *,
    skip_stun: bool = False,
) -> List[BattleEffect]:
    expired: List[BattleEffect] = []
    kept: List[BattleEffect] = []

    for effect in spirit.effects:
        if effect.type in (
            EffectType.debuff_burn,
            EffectType.debuff_poison,
            EffectType.debuff_freeze,
            EffectType.state_warmup,
            EffectType.state_channeling_skill,
            EffectType.state_shunt,
            EffectType.state_expansion,
        ):
            kept.append(effect)
            continue
        if skip_stun and effect.type == EffectType.debuff_stun:
            kept.append(effect)
            continue
        if effect.duration_turns is None:
            kept.append(effect)
            continue
        effect.duration_turns -= 1
        if effect.duration_turns <= 0:
            expired.append(effect)
        else:
            kept.append(effect)

    spirit.effects = kept
    return expired
