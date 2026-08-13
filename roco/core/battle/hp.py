"""HP mutation helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .context import BattleContext, TurnHost

from .types import BattleSpirit


def apply_damage(
    spirit: BattleSpirit,
    damage: int,
    *,
    ctx: "Optional[BattleContext]" = None,
) -> int:
    """Apply one damage segment to ``spirit``; return the post-mitigation amount.

    小琮灵珏减伤在 ``calculate_damage`` 管线内结算；致死时 ``on_death`` 可复活。
    ``ctx`` 仅用于复活战报。
    """
    from ..spirits import get_spirit_logic

    logic = get_spirit_logic(spirit.template_id)
    if logic is not None:
        damage = logic.adjust_incoming_damage(spirit, damage)

    reported = max(0, damage)
    applied = min(spirit.current_hp, reported)
    spirit.current_hp -= applied
    if spirit.current_hp <= 0:
        spirit.current_hp = 0
        spirit.is_alive = False
        if logic is not None:
            logic.on_death(spirit, ctx)
    return reported


def execute_instant_defeat(
    spirit: BattleSpirit,
    *,
    ctx: "Optional[TurnHost]" = None,
    log_message: Optional[str] = None,
) -> bool:
    """Lethal effect (e.g. freeze execute). Returns True if spirit remains alive (revived)."""
    from ..spirits import get_spirit_logic

    if not spirit.is_alive:
        return True
    logic = get_spirit_logic(spirit.template_id)
    spirit.current_hp = 0
    spirit.is_alive = False
    if logic is not None:
        logic.on_death(spirit, ctx)
    if spirit.is_alive:
        return True
    if ctx is not None and log_message:
        from .types import BattleLogType

        ctx.add_log(
            BattleLogType.spirit_defeated,
            log_message,
            {"targetId": spirit.unique_id},
        )
        ctx.notify_spirit_defeated(spirit)
    return False


def apply_heal(spirit: BattleSpirit, amount: float) -> int:
    """Apply up to missing HP; return the full requested heal amount."""
    reported = max(0, int(amount))
    missing = max(0, spirit.max_hp - spirit.current_hp)
    applied = min(missing, reported)
    spirit.current_hp += applied
    return reported
