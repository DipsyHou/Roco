"""Team-energy management, split out of the engine god object.

Owns all reads/writes of ``PlayerBattleData.team_energy`` and the per-skill
cost calculation (including spirit-specific modifiers). The engine composes an
``EnergyManager`` and delegates its public energy API to it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from .effects import adjust_skill_energy_cost
from .rules import TEAM_ENERGY_CAP_MAX, TEAM_ENERGY_MAX
from .types import BattleLogType, BattleSpirit
from . import messages as msg
from ..spirits import get_spirit_logic

if TYPE_CHECKING:
    from .engine import BattleEngine


def skill_team_energy_cost(actor: BattleSpirit, skill) -> int:
    """Team-energy cost for ``skill`` after spirit + effect modifiers.

    Shared by the engine and the remote engine so both agree on cost.
    """
    base = max(0, skill.energy_cost or 0)
    logic = get_spirit_logic(actor.template_id)
    if logic:
        base = logic.get_skill_energy_cost(actor, skill, base)
    return adjust_skill_energy_cost(actor, skill.id, base)


class EnergyManager:
    def __init__(self, engine: "BattleEngine") -> None:
        self._eng = engine

    @property
    def _state(self):
        return self._eng.state

    def cost(self, actor: BattleSpirit, skill) -> int:
        return skill_team_energy_cost(actor, skill)

    def can_pay(self, player_id: str, actor: BattleSpirit, skill) -> bool:
        logic = get_spirit_logic(actor.template_id)
        if logic and not logic.should_use_team_energy(actor, skill):
            return True
        pd = self._state.players.get(player_id)
        if not pd:
            return False
        return pd.team_energy >= self.cost(actor, skill)

    def spend(self, player_id: str, actor: BattleSpirit, skill) -> None:
        logic = get_spirit_logic(actor.template_id)
        if logic and not logic.should_use_team_energy(actor, skill):
            return
        pd = self._state.players.get(player_id)
        if not pd:
            return
        cost = self.cost(actor, skill)
        if cost <= 0:
            return
        pd.team_energy = max(0, pd.team_energy - cost)
        pd.team_energy_spent_tracker += cost
        for spirit in self._eng.get_all_spirits(player_id):
            if not spirit.is_alive:
                continue
            observer_logic = get_spirit_logic(spirit.template_id)
            if observer_logic:
                observer_logic.on_team_energy_spent(
                    self._eng, player_id, spirit, cost, actor
                )

    def gain(
        self,
        player_id: str,
        amount: int,
        *,
        reason: Optional[str] = None,
        log_type: Any = None,
        silent: bool = False,
    ) -> int:
        pd = self._state.players.get(player_id)
        if not pd or amount <= 0:
            return 0
        before = pd.team_energy
        pd.team_energy = min(pd.max_team_energy, pd.team_energy + amount)
        gained = pd.team_energy - before
        if gained > 0 and not silent:
            if reason:
                message = msg.team_energy_reason(reason, pd.team_energy, pd.max_team_energy)
            else:
                message = msg.team_energy_gain(
                    player_id, gained, pd.team_energy, pd.max_team_energy
                )
            self._eng.add_log(
                log_type or BattleLogType.effect_applied,
                message,
                {"playerId": player_id, "teamEnergy": pd.team_energy},
            )
        return gained

    def sync_cap(self, player_id: str) -> int:
        pd = self._state.players.get(player_id)
        if not pd:
            return TEAM_ENERGY_MAX
        bonus = 0
        for spirit in self._eng.get_all_spirits(player_id):
            if not spirit.is_alive:
                continue
            logic = get_spirit_logic(spirit.template_id)
            if logic:
                bonus = max(bonus, logic.get_team_energy_cap_bonus(self._eng, spirit))
        pd.max_team_energy = min(TEAM_ENERGY_CAP_MAX, TEAM_ENERGY_MAX + bonus)
        if pd.team_energy > pd.max_team_energy:
            pd.team_energy = pd.max_team_energy
        return pd.max_team_energy

    def get_spent(self, player_id: str) -> int:
        pd = self._state.players.get(player_id)
        return pd.team_energy_spent_tracker if pd else 0

    def reset_spent(self, player_id: str) -> None:
        pd = self._state.players.get(player_id)
        if pd:
            pd.team_energy_spent_tracker = 0
