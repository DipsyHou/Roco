"""BattleEngine public wrappers around EnergyManager.

This mixin is the API layer for team-energy read/write operations; the actual
accounting lives in `energy.py`.
"""

from __future__ import annotations

from typing import Any, Optional

from .types import BattleSpirit


class EnergyFacadeMixin:
    def _can_pay_team_energy(self, player_id: str, actor: BattleSpirit, skill) -> bool:
        return self._energy.can_pay(player_id, actor, skill)

    def _team_energy_cost(self, actor: BattleSpirit, skill) -> int:
        return self._energy.cost(actor, skill)

    def effective_skill_energy_cost(self, actor: BattleSpirit, skill) -> int:
        """Public helper for UIs: team-energy cost after spirit-specific modifiers."""
        return self._energy.cost(actor, skill)

    def gain_team_energy(
        self,
        player_id: str,
        amount: int,
        *,
        reason: Optional[str] = None,
        log_type: Any = None,
        silent: bool = False,
    ) -> int:
        return self._energy.gain(
            player_id, amount, reason=reason, log_type=log_type, silent=silent
        )

    # Back-compat internal alias.
    _gain_team_energy = gain_team_energy

    def sync_team_energy_cap(self, player_id: str) -> int:
        return self._energy.sync_cap(player_id)

    def get_team_energy_spent(self, player_id: str) -> int:
        return self._energy.get_spent(player_id)

    def reset_team_energy_spent(self, player_id: str) -> None:
        self._energy.reset_spent(player_id)

    def _spend_team_energy(self, player_id: str, actor: BattleSpirit, skill) -> None:
        self._energy.spend(player_id, actor, skill)
