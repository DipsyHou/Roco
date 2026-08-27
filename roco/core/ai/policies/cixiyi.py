"""石化刺蜥蜴 AI."""

from __future__ import annotations

from typing import Any, Dict

from ...battle.shield import has_shield_from
from ...battle.engine import BattleEngine
from ...battle.types import ActionType, BattleSpirit
from .. import features as F


class CixiyiPolicy:
    template_id = "cixiyi"

    def score(
        self,
        engine: BattleEngine,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> float:
        at = action.get("type")
        energy = F.team_energy(engine, actor.owner_id)
        main_c = F.main_c_ally(engine, actor.owner_id)

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            return 120.0 if energy < 3 else 10.0

        if at == ActionType.normal_attack.value:
            enemy = engine.find_spirit_anywhere(action.get("targetId") or "")
            if not enemy:
                return 5.0
            return 18.0 + (1.0 - F.hp_ratio(enemy)) * 18.0

        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        target_id = action.get("targetId")
        target = engine.find_spirit_anywhere(target_id) if target_id else None
        main_c_id = main_c.unique_id if main_c else None

        if skill_id == "cixiyi_skill1":
            if energy < 3:
                return -40.0
            missing = F.ally_missing_shield_from(engine, actor.owner_id, actor.unique_id)
            if missing is None:
                return 8.0
            score = 140.0
            if missing.unique_id == main_c_id:
                score += 15.0
            return score

        if skill_id == "cixiyi_skill2":
            if not target:
                return -50.0
            score = 100.0 + (1.0 - F.hp_ratio(target)) * 35.0
            if target.unique_id == main_c_id:
                score += 10.0
            if has_shield_from(actor, actor.unique_id):
                score += 10.0
            return score

        return 0.0
