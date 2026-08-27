"""Static spirit templates."""

from __future__ import annotations

from typing import Dict, List, Optional

from ...battle.types import SpiritTemplate

from .flora import FLORA
from .clawdragon import CLAWDRAGON
from .parsas import PARSAS
from .chaosling import CHAOSLING
from .starweaver import STARWEAVER
from .steamdragon import STEAMDRAGON
from .qiuka import QIUKA
from .fanying import FANYING
from .tita import TITA
from .cuiding import CUIDING
from .guifashi import GUIFASHI
from .guagua import GUAGUA
from .xiaozong import XIAOZONG
from .bahamut import BAHAMUT
from .daermao import DAERMAO
from .huxian import HUXIAN
from .shengyu import SHENGYU
from .deerle import DEERLE
from .tengjiao import TENGJIAO
from .emozhanshi import EMOZHANSHI
from .cixiyi import CIXIYI
from .jifangfang import JIFANGFANG

ALL_SPIRITS: List[SpiritTemplate] = [
    FLORA,
    CLAWDRAGON,
    PARSAS,
    CHAOSLING,
    STARWEAVER,
    STEAMDRAGON,
    QIUKA,
    FANYING,
    TITA,
    CUIDING,
    GUIFASHI,
    GUAGUA,
    XIAOZONG,
    BAHAMUT,
    DAERMAO,
    HUXIAN,
    SHENGYU,
    DEERLE,
    TENGJIAO,
    EMOZHANSHI,
    CIXIYI,
    JIFANGFANG,
]

SPIRIT_BY_ID: Dict[str, SpiritTemplate] = {s.id: s for s in ALL_SPIRITS}


def get_spirit_template(sid: str) -> Optional[SpiritTemplate]:
    return SPIRIT_BY_ID.get(sid)


__all__ = [
    'ALL_SPIRITS',
    'SPIRIT_BY_ID',
    'get_spirit_template',
    'FLORA', 'CLAWDRAGON', 'PARSAS', 'CHAOSLING', 'STARWEAVER', 'STEAMDRAGON', 'QIUKA', 'FANYING', 'TITA', 'CUIDING', 'GUIFASHI', 'GUAGUA', 'XIAOZONG', 'BAHAMUT', 'DAERMAO', 'HUXIAN', 'SHENGYU', 'DEERLE', 'TENGJIAO', 'EMOZHANSHI', 'CIXIYI', 'JIFANGFANG',
]
