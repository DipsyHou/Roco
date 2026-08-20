"""Battle lifecycle notifications and win-condition checks.

Keep battle-end detection and defeat broadcasts here so other modules do not
need to duplicate win-condition logic.
"""

from __future__ import annotations

from .types import BattleLogType, BattlePhase, BattleSpirit
from . import messages as msg
from ..spirits import get_spirit_logic


class BattleLifecycleMixin:
    def notify_spirit_defeated(self, defeated: BattleSpirit) -> None:
        for pid in self._player_ids:
            for spirit in self.state.players[pid].spirits:
                spirit_logic = get_spirit_logic(spirit.template_id)
                if spirit_logic:
                    spirit_logic.on_spirit_defeated(self, spirit, defeated)

    def _check_battle_end(self) -> bool:
        for pid in self._player_ids:
            pd = self.state.players[pid]
            if all(not s.is_alive for s in pd.spirits):
                winner = self.get_opponent_id(pid)
                self.state.phase = BattlePhase.finished
                self.state.winner_id = winner
                self.state.active_actor_id = None
                self.add_log(
                    BattleLogType.battle_end,
                    msg.battle_end(winner),
                    {"winnerId": winner},
                )
                return True
        return False
