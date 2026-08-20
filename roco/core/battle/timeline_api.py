"""Timeline-facing BattleEngine mixin.

This is the engine-facing API for timeline and turn-preparation operations.
The actual scheduling math lives in `timeline.py` and `timeline_controller.py`.
"""

from __future__ import annotations

from typing import List

from .types import BattlePhase, BattleSpirit
from ..spirits import get_spirit_logic


class TimelineMixin:
    def _all_alive_spirits(self) -> List[BattleSpirit]:
        return self._timeline.all_alive_spirits()

    def after_actor_acts(self, actor: BattleSpirit) -> None:
        logic = get_spirit_logic(actor.template_id)
        if logic and actor.is_alive:
            logic.on_after_actor_acts(self, actor)

    def get_effective_speed(self, spirit: BattleSpirit) -> float:
        return self._timeline.get_effective_speed(spirit)

    def advance_action(self, target: BattleSpirit, percent: float) -> None:
        self._timeline.advance_action(target, percent)

    def delay_action(self, target: BattleSpirit, percent: float) -> None:
        self._timeline.delay_action(target, percent)

    def _set_active_actor(self) -> None:
        self.state.active_actor_id = self._timeline.pick_next_actor_id()
        self.state.turn_prepared_actor_id = None
        self.state.active_turn_stunned = False

    def advance_past_dead_active(self) -> None:
        """Active actor died before acting; pick next live actor."""
        if self.state.phase == BattlePhase.finished:
            return
        self.state.turn_prepared_actor_id = None
        self.state.active_turn_stunned = False
        self._set_active_actor()
        self._refresh_timeline_preview()
        if self._check_battle_end():
            return
        self._begin_turn_if_needed()

    # Back-compat internal alias (pre-existing call sites).
    _advance_past_dead_active = advance_past_dead_active

    def ensure_active_turn_begun(self) -> None:
        """轮到行动者时先结算行动开始系统处理，再等待玩家输入。"""
        self._begin_turn_if_needed()

    def _begin_turn_if_needed(self) -> None:
        actor_id = self.state.active_actor_id
        if not actor_id or actor_id == self.state.turn_prepared_actor_id:
            return
        actor = self.find_spirit_anywhere(actor_id)
        if not actor:
            return
        if not actor.is_alive:
            self._advance_past_dead_active()
            return
        self._timeline.advance_time_to_actor(actor)
        self.state.active_turn_stunned = self._pipeline.begin_turn(actor)
        self.state.turn_prepared_actor_id = actor_id
        if not actor.is_alive:
            self._advance_past_dead_active()

    def _refresh_timeline_preview(self) -> None:
        self._timeline.refresh_preview()
