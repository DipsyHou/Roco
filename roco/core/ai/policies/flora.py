"""蹦蹦种子 AI."""

from __future__ import annotations

from typing import Any, Dict

from ...battle.engine import BattleEngine
from ...battle.types import ActionType, BattleSpirit, EffectType
from .. import features as F


class FloraPolicy:
    template_id = "flora"

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
        lowest = F.lowest_hp_ally(engine, actor.owner_id)

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            if energy < 2:
                return 150.0
            if energy < 4:
                return 60.0
            return 10.0

        if at == ActionType.normal_attack.value:
            enemy = engine.find_spirit_anywhere(action.get("targetId") or "")
            if not enemy:
                return 5.0
            return 20.0 + (1.0 - F.hp_ratio(enemy)) * 20.0

        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        target_id = action.get("targetId")
        target = engine.find_spirit_anywhere(target_id) if target_id else None

        if skill_id == "flora_skill1":  # 光合作用
            if not target:
                return -50.0
            r = F.hp_ratio(target)
            if r >= 0.5:
                return -20.0
            score = 130.0 + (0.5 - r) * 180.0
            if lowest and target.unique_id == lowest.unique_id:
                score += 25.0
            if target.unique_id == main_c_id:
                score += 15.0
            return score

        if skill_id == "flora_skill2":  # 抗逆
            if not target:
                return -50.0
            if F.has_effect(target, EffectType.buff_taken_damage_percent_reduction):
                return -40.0
            score = 120.0
            if target.unique_id == main_c_id:
                score += 30.0
            if F.hp_ratio(target) < 0.65:
                score += 10.0
            return score

        if skill_id == "flora_skill3":  # 麻醉
            if energy < 7:
                return -30.0
            return 120.0 + (energy - 7) * 12.0

        return 0.0
