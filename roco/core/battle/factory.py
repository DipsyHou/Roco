"""Battle entity construction helpers."""

from __future__ import annotations

import copy
import uuid

from .timeline import ACTION_GAP
from .types import BattleSpirit, SpiritTemplate
from .stats import bind_spirit_stat_engine
from ..spirits import get_spirit_logic


def create_battle_spirit(
    template: SpiritTemplate,
    owner_id: str,
    slot: int,
) -> BattleSpirit:
    bs = template.base_stats
    spirit = BattleSpirit(
        unique_id=str(uuid.uuid4()),
        template_id=template.id,
        owner_id=owner_id,
        name=template.name,
        base_stats=copy.deepcopy(bs),
        current_hp=bs.hp,
        max_hp=bs.hp,
        slot=slot,
        charge=float(ACTION_GAP),
        effects=[],
        skill_cooldowns={},
        is_alive=True,
    )
    logic = get_spirit_logic(template.id)
    if logic:
        logic.on_unit_created(spirit)
    return spirit


def bind_and_start_spirit(engine, spirit: BattleSpirit) -> None:
    """Attach engine-backed stat queries and fire battle-start hooks."""
    bind_spirit_stat_engine(spirit, engine)
    logic = get_spirit_logic(spirit.template_id)
    if logic:
        logic.on_battle_start(engine, spirit)
