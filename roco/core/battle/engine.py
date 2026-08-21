"""Timeline battle engine — 5v5 action-value scheduler."""

from __future__ import annotations

import secrets
from typing import Any, Dict, List, Optional

from .action_executor import ActionExecutor
from .action_submission import ActionSubmissionMixin
from .context_api import BattleContextMixin
from .energy import EnergyManager
from .energy_facade import EnergyFacadeMixin
from .extra_action_queue import ExtraActionQueueMixin
from .factory import bind_and_start_spirit, create_battle_spirit
from .lifecycle import BattleLifecycleMixin
from .rng import RandomSource
from .rules import MAX_TEAM_SIZE, MIN_TEAM_SIZE
from .timeline_api import TimelineMixin
from .timeline_controller import TimelineController
from .turn_pipeline import TurnPipeline
from .types import BattleLogType, BattlePhase, BattleState, PlayerBattleData, SpiritTemplate
from . import messages as msg


class BattleEngine(
    BattleContextMixin,
    TimelineMixin,
    ExtraActionQueueMixin,
    ActionSubmissionMixin,
    EnergyFacadeMixin,
    BattleLifecycleMixin,
):
    def __init__(
        self,
        battle_id: str,
        player1_id: str,
        player2_id: str,
        p1_templates: List[SpiritTemplate],
        p2_templates: List[SpiritTemplate],
    ) -> None:
        for label, team in [("Player 1", p1_templates), ("Player 2", p2_templates)]:
            n = len(team)
            if n < MIN_TEAM_SIZE or n > MAX_TEAM_SIZE:
                raise ValueError(
                    f"{label} needs {MIN_TEAM_SIZE}~{MAX_TEAM_SIZE} spirits, got {n}"
                )

        self._player_ids = [player1_id, player2_id]
        self.state = BattleState(
            battle_id=battle_id,
            phase=BattlePhase.waiting_for_action,
            action_count=0,
            rng_seed=secrets.token_hex(8),
            players={
                player1_id: PlayerBattleData(
                    player_id=player1_id,
                    spirits=[
                        create_battle_spirit(t, player1_id, i + 1)
                        for i, t in enumerate(p1_templates)
                    ],
                ),
                player2_id: PlayerBattleData(
                    player_id=player2_id,
                    spirits=[
                        create_battle_spirit(t, player2_id, i + 1)
                        for i, t in enumerate(p2_templates)
                    ],
                ),
            },
            battle_log=[],
        )
        self._pipeline = TurnPipeline(self)
        self._energy = EnergyManager(self)
        self._actions = ActionExecutor(self)
        self._timeline = TimelineController(self)
        self._rng = RandomSource(self.state.rng_seed, self.state.rng_counters)
        self._suspended_turn_actor_id: Optional[str] = None
        self._suspended_turn_action: Optional[Dict[str, Any]] = None
        self._suspended_turn_stunned: bool = False

        for pid in self._player_ids:
            for spirit in self.state.players[pid].spirits:
                bind_and_start_spirit(self, spirit)

        self.add_log(BattleLogType.turn_start, msg.BATTLE_START)
        self._set_active_actor()
        self._refresh_timeline_preview()


__all__ = ["BattleEngine", "create_battle_spirit"]
