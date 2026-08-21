"""Extra-action queue operations for inserted turns.

This module only manages queue state and activation order for inserted action
slots. It does not decide when actions are generated.
"""

from __future__ import annotations

from typing import List, Optional

from .extra_action import ExtraActionSlot


class ExtraActionQueueMixin:
    def current_extra_slot(self) -> Optional[ExtraActionSlot]:
        q = self.state.extra_action_queue
        return q[0] if q else None

    def queue_extra_actions(
        self,
        slots: List[ExtraActionSlot],
        *,
        front: bool = False,
    ) -> None:
        """Append (default) or insert-at-front a list of extra-action slots."""
        valid: List[ExtraActionSlot] = []
        for slot in slots:
            spirit = self.find_spirit_anywhere(slot.actor_id)
            if spirit and spirit.is_alive:
                valid.append(slot)
        if not valid:
            return
        if front:
            self.state.extra_action_queue = list(valid) + self.state.extra_action_queue
        else:
            self.state.extra_action_queue = self.state.extra_action_queue + list(valid)

    def _prune_extra_action_queue(self) -> None:
        kept: List[ExtraActionSlot] = []
        for slot in self.state.extra_action_queue:
            spirit = self.find_spirit_anywhere(slot.actor_id)
            if spirit and spirit.is_alive:
                kept.append(slot)
        self.state.extra_action_queue = kept

    def _activate_extra_slot(self, slot: ExtraActionSlot) -> bool:
        actor = self.find_spirit_anywhere(slot.actor_id)
        if not actor or not actor.is_alive:
            return False
        self.state.active_actor_id = actor.unique_id
        self.state.turn_prepared_actor_id = actor.unique_id
        self.state.active_turn_stunned = False
        return True

    def _advance_to_next_extra_slot(self) -> bool:
        """Pop dead slots; activate next live one. Returns True if any activated."""
        self._prune_extra_action_queue()
        while self.state.extra_action_queue:
            if self._activate_extra_slot(self.state.extra_action_queue[0]):
                return True
            self.state.extra_action_queue.pop(0)
        return False

    def _pop_resolved_slot(self, resolved: ExtraActionSlot) -> None:
        """Remove the slot we just resolved. Tolerates queue mutation by logic."""
        q = self.state.extra_action_queue
        for i, s in enumerate(q):
            if s is resolved or (
                s.actor_id == resolved.actor_id and s.policy_id == resolved.policy_id
            ):
                q.pop(i)
                return
