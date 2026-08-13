"""Backward-compatible battle helper exports.

New code should import from the narrower modules:
``stats``, ``damage``, ``effects``, ``hp``, or ``dot``.
"""

from __future__ import annotations

from .damage import (
    calculate_damage,
    get_damage_caps,
    get_damage_modifiers,
    get_flat_damage_modifiers,
    get_incoming_damage_modifiers,
    get_incoming_flat_damage_modifiers,
)
from .dot import (
    process_burn_on_action_end,
    process_poison_damage,
    process_poison_on_action_end,
    process_system_effects_on_action_end,
    trigger_burn_damage,
    trigger_poison_damage,
)
from .effects import (
    add_warmup_stacks,
    apply_burn_stacks,
    apply_poison_stacks,
    get_burn_effects,
    get_poison_effect,
    get_poison_stacks,
    get_total_burn_stacks,
    get_warmup_effect,
    get_warmup_stacks,
    is_action_blocked,
    is_debuff_immune,
    is_stunned,
    make_effect,
    purge_debuffs,
    tick_effects,
    tick_warmup_stacks,
)
from .hp import apply_damage, apply_heal
from .stats import (
    count_state_effects,
    get_effective_speed,
    get_effective_stat,
    get_state_stack_count,
    is_debuff_effect,
    is_state_effect,
)

__all__ = [
    "add_warmup_stacks",
    "apply_burn_stacks",
    "apply_damage",
    "apply_heal",
    "apply_poison_stacks",
    "calculate_damage",
    "count_state_effects",
    "get_burn_effects",
    "get_damage_caps",
    "get_damage_modifiers",
    "get_effective_speed",
    "get_effective_stat",
    "get_flat_damage_modifiers",
    "get_incoming_damage_modifiers",
    "get_incoming_flat_damage_modifiers",
    "get_poison_effect",
    "get_poison_stacks",
    "get_state_stack_count",
    "get_total_burn_stacks",
    "get_warmup_effect",
    "get_warmup_stacks",
    "is_action_blocked",
    "is_debuff_effect",
    "is_debuff_immune",
    "is_state_effect",
    "is_stunned",
    "make_effect",
    "process_burn_on_action_end",
    "process_poison_damage",
    "process_poison_on_action_end",
    "process_system_effects_on_action_end",
    "purge_debuffs",
    "tick_effects",
    "tick_warmup_stacks",
    "trigger_burn_damage",
    "trigger_poison_damage",
]
