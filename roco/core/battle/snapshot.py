"""Action-scoped state snapshots for exception rollback.

If a spirit's skill logic raises midway, the battle can be left half-resolved:
energy already spent, the first damage segment applied, effects partially
attached. Continuing from there silently corrupts the match — and in online
play that corrupt state is broadcast to both clients. The engine therefore
snapshots before each action and restores on exception.

Two constraints shape the implementation:

- **Restore in place.** Collaborators hold live references into the state:
  ``RandomSource`` keeps ``BattleState.rng_counters`` itself (see rng.py). So we
  mutate the existing ``BattleState`` rather than rebinding ``engine.state``,
  which would silently orphan those references.
- **Skip the battle log.** It is append-only, and deep-copying it dominates the
  cost (~8 ms at 1000 entries vs ~0.3 ms without). We record its length and
  truncate back instead, which also preserves log entries by identity.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .extra_action import ExtraActionSlot
from .types import BattleLogEntry, BattlePhase, PlayerBattleData


@dataclass
class StateSnapshot:
    """Everything an action may mutate, minus the append-only battle log."""

    phase: BattlePhase
    action_count: int
    players: Dict[str, PlayerBattleData]
    active_actor_id: Optional[str]
    turn_prepared_actor_id: Optional[str]
    active_turn_stunned: bool
    extra_action_queue: List[ExtraActionSlot]
    timeline_preview: List[str]
    winner_id: Optional[str]
    rng_counters: Dict[str, int]
    log_length: int
    # Engine-level suspended-turn bookkeeping (not part of BattleState).
    suspended_turn_actor_id: Optional[str]
    suspended_turn_action: Optional[Dict[str, Any]]
    suspended_turn_stunned: bool


def take_snapshot(engine: Any) -> StateSnapshot:
    """Capture pre-action state. Cost is independent of battle-log length."""
    state = engine.state
    return StateSnapshot(
        phase=state.phase,
        action_count=state.action_count,
        players=copy.deepcopy(state.players),
        active_actor_id=state.active_actor_id,
        turn_prepared_actor_id=state.turn_prepared_actor_id,
        active_turn_stunned=state.active_turn_stunned,
        extra_action_queue=copy.deepcopy(state.extra_action_queue),
        timeline_preview=list(state.timeline_preview),
        winner_id=state.winner_id,
        rng_counters=dict(state.rng_counters),
        log_length=len(state.battle_log),
        suspended_turn_actor_id=engine._suspended_turn_actor_id,
        suspended_turn_action=(
            dict(engine._suspended_turn_action)
            if engine._suspended_turn_action is not None
            else None
        ),
        suspended_turn_stunned=engine._suspended_turn_stunned,
    )


def restore_snapshot(engine: Any, snap: StateSnapshot) -> List[BattleLogEntry]:
    """Roll ``engine`` back to ``snap``; return the discarded log entries.

    Mutates the existing ``BattleState`` in place (see module docstring). The
    returned entries are the partial action's log output — the caller may keep
    them for diagnostics, but they are no longer part of the battle log.

    Note that ``state.players`` is replaced wholesale, so any ``BattleSpirit``
    reference obtained before the action becomes stale. Re-resolve spirits via
    ``find_spirit_anywhere`` after a rollback instead of reusing old handles.
    """
    state = engine.state
    state.phase = snap.phase
    state.action_count = snap.action_count
    state.players = snap.players
    state.active_actor_id = snap.active_actor_id
    state.turn_prepared_actor_id = snap.turn_prepared_actor_id
    state.active_turn_stunned = snap.active_turn_stunned
    state.extra_action_queue = snap.extra_action_queue
    state.timeline_preview = list(snap.timeline_preview)
    state.winner_id = snap.winner_id

    # In-place so RandomSource's live reference keeps working.
    state.rng_counters.clear()
    state.rng_counters.update(snap.rng_counters)

    discarded = state.battle_log[snap.log_length:]
    del state.battle_log[snap.log_length:]

    engine._suspended_turn_actor_id = snap.suspended_turn_actor_id
    engine._suspended_turn_action = snap.suspended_turn_action
    engine._suspended_turn_stunned = snap.suspended_turn_stunned

    from .stats import bind_spirit_stat_engine

    for pd in state.players.values():
        for spirit in pd.spirits:
            bind_spirit_stat_engine(spirit, engine)

    return discarded
