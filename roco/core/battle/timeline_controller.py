"""Timeline / turn-order mechanics, split from the engine.

Owns charge accounting, effective-speed aggregation, next-actor selection and the
timeline preview. Turn orchestration (begin/act/end, battle-end) stays in the
engine; this controller only answers "who is next" and "advance the clock".
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from .stats import get_effective_stat
from .timeline import (
    ACTION_GAP,
    TIMELINE_PREVIEW_COUNT,
    action_value,
    adjust_charge_advance,
    adjust_charge_delay,
    compute_timeline_preview,
    pick_next_actor,
)
from .types import BattleSpirit, StatType
from ..spirits import get_spirit_logic

if TYPE_CHECKING:
    from .engine import BattleEngine


class TimelineController:
    def __init__(self, engine: "BattleEngine") -> None:
        self._eng = engine

    def all_alive_spirits(self) -> List[BattleSpirit]:
        eng = self._eng
        result: List[BattleSpirit] = []
        for pid in eng.player_ids:
            result.extend(eng.get_active_spirits(pid))
        return result

    def get_effective_speed(self, spirit: BattleSpirit) -> float:
        eng = self._eng
        speed_pct_bonus = 0.0
        for pid in eng.player_ids:
            for source in eng.state.players[pid].spirits:
                if not source.is_alive:
                    continue
                logic = get_spirit_logic(source.template_id)
                if logic:
                    speed_pct_bonus += logic.get_aura_stat_percent_bonus(
                        eng, source, spirit, StatType.speed
                    )
        speed = get_effective_stat(
            spirit,
            StatType.speed,
            extra_percent_bonus=speed_pct_bonus,
        )
        return max(1, speed)

    def pick_next_actor_id(self) -> Optional[str]:
        alive = self.all_alive_spirits()
        if not alive:
            return None
        entries = [
            (s, s.charge, max(1, self.get_effective_speed(s)), s.unique_id)
            for s in alive
        ]
        actor = pick_next_actor(entries)
        return actor.unique_id if actor else None

    def advance_time_to_actor(self, actor: BattleSpirit) -> None:
        alive = self.all_alive_spirits()
        v = action_value(actor.charge, max(1, self.get_effective_speed(actor)))
        for s in alive:
            s.charge -= v * max(1, self.get_effective_speed(s))
        actor.charge = max(0.0, actor.charge) + ACTION_GAP

    def advance_action(self, target: BattleSpirit, percent: float) -> None:
        target.charge = adjust_charge_advance(target.charge, percent)

    def delay_action(self, target: BattleSpirit, percent: float) -> None:
        target.charge = adjust_charge_delay(target.charge, percent)

    def refresh_preview(self) -> None:
        eng = self._eng
        alive = self.all_alive_spirits()
        preview = compute_timeline_preview(
            alive,
            lambda s: s.charge,
            lambda s: max(1, self.get_effective_speed(s)),
            lambda s: s.unique_id,
            count=TIMELINE_PREVIEW_COUNT,
        )
        eng.state.timeline_preview = [s.unique_id for s in preview]
