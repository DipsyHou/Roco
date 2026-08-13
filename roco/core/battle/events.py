"""Damage events — single dispatch path for hook observers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional

from .types import BattleSpirit

if TYPE_CHECKING:
    from .engine import BattleEngine


class DamageSource(str, Enum):
    """How damage was dealt (for hook filtering)."""

    attack = "attack"
    skill = "skill"
    dot = "dot"
    fixed = "fixed"
    # 附加伤害：结算与同类型普通伤害相同，但不构成一次「发动攻击」。
    additional = "additional"
    other = "other"


@dataclass(frozen=True)
class DamageEvent:
    attacker: Optional[BattleSpirit]
    target: BattleSpirit
    damage: int
    source: DamageSource = DamageSource.other


def dispatch_damage(ctx: "BattleEngine", event: DamageEvent) -> None:
    """Notify hooks after HP has been reduced.

    Hook order for one damage event:
    1. ``on_damage`` — every alive spirit (player order, then roster order)
    2. ``on_ally_damage_dealt`` — attacker's teammates
    3. ``on_attack_hit`` — attacker, only for attack/skill sources
    """
    from ..spirits import get_spirit_logic

    if event.damage < 0:
        return

    attacker = event.attacker
    target = event.target

    for pid in ctx.player_ids:
        for spirit in ctx.state.players[pid].spirits:
            if not spirit.is_alive:
                continue
            logic = get_spirit_logic(spirit.template_id)
            if logic:
                logic.on_damage(ctx, spirit, event)

    if attacker and attacker.is_alive:
        owner_id = attacker.owner_id
        for spirit in ctx.get_all_spirits(owner_id):
            if not spirit.is_alive:
                continue
            logic = get_spirit_logic(spirit.template_id)
            if logic:
                logic.on_ally_damage_dealt(ctx, spirit, event)

        if event.source in (DamageSource.attack, DamageSource.skill):
            atk_logic = get_spirit_logic(attacker.template_id)
            if atk_logic:
                atk_logic.on_attack_hit(ctx, owner_id, attacker, target, event.damage)

    if not target.is_alive:
        ctx.notify_spirit_defeated(target)
