"""BattleEngine action submission lifecycle.

This module owns the orchestration of one submitted action: validation,
snapshot/rollback, extra-action suspension, and normal turn completion.
Damage math and spirit-specific effects live elsewhere.
"""

from __future__ import annotations

import logging
from typing import Optional

from .actions import ActionDict
from .extra_action import policy_allows
from .snapshot import restore_snapshot, take_snapshot
from .types import ActionType, BattleLogType, BattlePhase, BattleSpirit
from . import messages as msg
from ..spirits import get_spirit_logic, get_spirit_template

logger = logging.getLogger(__name__)


class ActionSubmissionMixin:
    def submit_action(self, player_id: str, action: ActionDict) -> bool:
        if self.state.phase != BattlePhase.waiting_for_action:
            return False
        actor_id = self.state.active_actor_id
        if not actor_id:
            return False
        actor = self.find_spirit_anywhere(actor_id)
        if not actor or actor.owner_id != player_id:
            return False

        preview_result = self._preview_action(player_id, actor, action)
        if preview_result is not None:
            return preview_result

        slot = self.current_extra_slot()
        if slot:
            if not self._validate_action(player_id, action, actor):
                return False
            snapshot = take_snapshot(self)
            self.state.phase = BattlePhase.processing
            try:
                self._pipeline.resolve_inserted_extra_action(actor, action)
            except Exception:  # noqa: BLE001
                self._abort_action(snapshot, actor, action)
                return False
            if self._check_battle_end():
                return True
            self._pop_resolved_slot(slot)
            if self._advance_to_next_extra_slot():
                self._refresh_timeline_preview()
                self.state.phase = BattlePhase.waiting_for_action
                return True
            return self._finish_suspended_turn_if_any()

        self.ensure_active_turn_begun()
        if not self._validate_action(player_id, action, actor):
            return False

        snapshot = take_snapshot(self)
        self.state.phase = BattlePhase.processing
        try:
            self._process_action_turn(actor, action)
        except Exception:  # noqa: BLE001
            self._abort_action(snapshot, actor, action)
            return False

        if self._check_battle_end():
            return True

        stunned = self.state.active_turn_stunned
        if self._advance_to_next_extra_slot():
            self._suspended_turn_actor_id = actor.unique_id
            self._suspended_turn_action = dict(action)
            self._suspended_turn_stunned = stunned
            self._refresh_timeline_preview()
            self.state.phase = BattlePhase.waiting_for_action
            return True

        return self._finish_normal_turn(player_id, actor, action, stunned)

    def _preview_action(
        self,
        player_id: str,
        actor: BattleSpirit,
        action: ActionDict,
    ) -> Optional[bool]:
        """Dispatch non-consuming preview actions to spirit logic."""
        if not action.get("previewDish"):
            return None
        logic = get_spirit_logic(actor.template_id)
        if not logic:
            return False
        return logic.preview_action(self, player_id, actor, action)

    def _abort_action(
        self,
        snapshot,
        actor: BattleSpirit,
        action: ActionDict,
    ) -> None:
        """Roll back a half-executed action and log the failure."""
        discarded = restore_snapshot(self, snapshot)
        logger.exception(
            "action failed: battle=%s actor=%s (%s) action=%s; rolled back, "
            "discarded %d log entr%s",
            self.state.battle_id,
            actor.unique_id,
            actor.template_id,
            action.get("skillId") or action.get("type"),
            len(discarded),
            "y" if len(discarded) == 1 else "ies",
        )
        self.add_log(
            BattleLogType.action_executed,
            msg.ACTION_EXCEPTION,
            {"actorId": actor.unique_id},
        )
        self.state.phase = BattlePhase.waiting_for_action

    def _finish_normal_turn(
        self,
        player_id: str,
        actor: BattleSpirit,
        action: ActionDict,
        stunned: bool,
    ) -> bool:
        self._pipeline.end_turn(actor, action, player_id=player_id, stunned=stunned)
        if self._check_battle_end():
            return True
        self.state.action_count += 1
        pd = self.state.players.get(player_id)
        if pd:
            pd.team_energy_spent_tracker = 0
        self._set_active_actor()
        self._refresh_timeline_preview()
        self._begin_turn_if_needed()
        self.state.phase = BattlePhase.waiting_for_action
        return True

    def _finish_suspended_turn_if_any(self) -> bool:
        """Resume normal turn-end processing after the extra-action queue drains."""
        actor_id = self._suspended_turn_actor_id
        action = self._suspended_turn_action
        stunned = self._suspended_turn_stunned
        self._suspended_turn_actor_id = None
        self._suspended_turn_action = None
        self._suspended_turn_stunned = False
        if not actor_id or action is None:
            if self.state.turn_prepared_actor_id:
                self.state.phase = BattlePhase.waiting_for_action
                return True
            self._set_active_actor()
            self._refresh_timeline_preview()
            self._begin_turn_if_needed()
            self.state.phase = BattlePhase.waiting_for_action
            return True
        actor = self.find_spirit_anywhere(actor_id)
        if not actor:
            self._set_active_actor()
            self._refresh_timeline_preview()
            self._begin_turn_if_needed()
            self.state.phase = BattlePhase.waiting_for_action
            return True
        return self._finish_normal_turn(actor.owner_id, actor, action, stunned)

    def _validate_action(
        self,
        player_id: str,
        action: ActionDict,
        actor: BattleSpirit,
    ) -> bool:
        at = action.get("type")
        aid = action.get("actorId")
        if aid != actor.unique_id:
            return False

        slot = self.current_extra_slot()
        if slot is not None:
            if slot.actor_id != actor.unique_id:
                return False
            if not policy_allows(slot, actor, action):
                return False

        logic = get_spirit_logic(actor.template_id)
        if logic:
            custom = logic.can_execute_action(
                self,
                actor,
                action,
                in_extra_action=slot is not None,
                stunned=self.state.active_turn_stunned,
            )
            if custom is not None and not custom[0]:
                return False

        if at in (ActionType.skip.value, ActionType.gather_energy.value):
            return actor.is_alive

        if at in (ActionType.normal_attack.value, ActionType.use_skill.value):
            if not actor.is_alive:
                return False
            if at == ActionType.use_skill.value:
                sk = action.get("skillId")
                if not sk:
                    return False
                tpl = get_spirit_template(actor.template_id)
                if not tpl or not any(s.id == sk for s in tpl.skills):
                    return False
                skill = next(s for s in tpl.skills if s.id == sk)
                logic = get_spirit_logic(actor.template_id)
                if logic:
                    custom = logic.can_use_skill(actor, skill)
                    if custom is not None:
                        return custom[0]
                if not self._can_pay_team_energy(player_id, actor, skill):
                    return False
            tid = action.get("targetId")
            if tid:
                target = self.find_spirit_anywhere(tid)
                if not target or not target.is_alive:
                    return False
            return True

        return False

    def _process_action_turn(
        self, actor: BattleSpirit, action: ActionDict
    ) -> None:
        self._pipeline.resolve_turn(
            actor,
            action,
            stunned=self.state.active_turn_stunned,
            defer_end_turn=True,
        )
