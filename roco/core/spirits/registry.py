"""template_id -> SpiritLogic"""

from __future__ import annotations

from typing import Dict, Optional

from .bahamut import bahamut_logic
from .base import SpiritLogic
from .chaosling import chaosling_logic
from .clawdragon import clawdragon_logic
from .fanying import fanying_logic
from .cuiding import cuiding_logic
from .daermao import daermao_logic
from .guifashi import guifashi_logic
from .huxian import huxian_logic
from .deerle import deerle_logic
from .parsas import parsas_logic
from .shengyu import shengyu_logic
from .tita import tita_logic
from .flora import flora_logic
from .qiuka import qiuka_logic
from .starweaver import starweaver_logic
from .steamdragon import steamdragon_logic
from .tengjiao import tengjiao_logic
from .xiaozong import xiaozong_logic

_REGISTRY: Dict[str, SpiritLogic] = {
    flora_logic.template_id: flora_logic,
    clawdragon_logic.template_id: clawdragon_logic,
    parsas_logic.template_id: parsas_logic,
    chaosling_logic.template_id: chaosling_logic,
    starweaver_logic.template_id: starweaver_logic,
    steamdragon_logic.template_id: steamdragon_logic,
    qiuka_logic.template_id: qiuka_logic,
    fanying_logic.template_id: fanying_logic,
    tita_logic.template_id: tita_logic,
    guifashi_logic.template_id: guifashi_logic,
    huxian_logic.template_id: huxian_logic,
    cuiding_logic.template_id: cuiding_logic,
    daermao_logic.template_id: daermao_logic,
    xiaozong_logic.template_id: xiaozong_logic,
    bahamut_logic.template_id: bahamut_logic,
    shengyu_logic.template_id: shengyu_logic,
    deerle_logic.template_id: deerle_logic,
    tengjiao_logic.template_id: tengjiao_logic,
}


def get_spirit_logic(template_id: str) -> Optional[SpiritLogic]:
    return _REGISTRY.get(template_id)
