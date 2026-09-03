"""机械方方 AI。"""

from __future__ import annotations

from typing import Any, Dict

from ...battle.engine import BattleEngine
from ...battle.types import ActionType, BattleSpirit, EffectType
from .. import features as F


class JifangfangPolicy:
    template_id = "jifangfang"

    def score(
        self,
        engine: BattleEngine,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> float:
        at = action.get("type")
        energy = F.team_energy(engine, actor.owner_id)
        main_c = F.main_c_ally(engine, actor.owner_id)
        main_c_id = main_c.unique_id if main_c else None
        missing_shield = F.ally_missing_shield_from(engine, actor.owner_id, actor.unique_id)

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            return 160.0 if energy <= 0 else 35.0 if energy < 3 else 4.0

        if at == ActionType.normal_attack.value:
            return -30.0

        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        target_id = action.get("targetId")
        target = engine.find_spirit_anywhere(target_id) if target_id else None

        if skill_id == "jifangfang_skill1":
            if energy < 3:
                return -50.0
            if missing_shield is None:
                return 10.0
            score = 150.0
            if missing_shield.unique_id == main_c_id:
                score += 25.0
            return score

        if skill_id == "jifangfang_skill2":
            if not target or target.owner_id != actor.owner_id:
                return -40.0
            if F.has_shield_from(target, actor.unique_id):
                return 10.0
            score = 140.0
            if target.unique_id == main_c_id:
                score += 20.0
            if F.hp_ratio(target) < 0.6:
                score += 10.0
            return score

        if skill_id == "jifangfang_skill3":
            if energy < 3:
                return -60.0
            score = 120.0
            if not any(e.type == EffectType.state_module_chaoxian for e in actor.effects):
                score += 20.0
            if energy >= 6:
                score += 10.0
            return score

        return 0.0
