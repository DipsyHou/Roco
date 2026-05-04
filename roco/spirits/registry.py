"""template_id -> SpiritLogic"""

from __future__ import annotations

from typing import Dict, Optional

from ..spirit_logic import SpiritLogic
from .chaosling import chaosling_logic
from .clawdragon import clawdragon_logic
from .flora import flora_logic
from .starweaver import starweaver_logic

_REGISTRY: Dict[str, SpiritLogic] = {
    flora_logic.template_id: flora_logic,
    clawdragon_logic.template_id: clawdragon_logic,
    chaosling_logic.template_id: chaosling_logic,
    starweaver_logic.template_id: starweaver_logic,
}


def get_spirit_logic(template_id: str) -> Optional[SpiritLogic]:
    return _REGISTRY.get(template_id)
