"""蹦蹦种子 AI."""

from __future__ import annotations

from typing import Any, Dict

from ...battle.engine import BattleEngine
from ...battle.types import ActionType, BattleSpirit
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
        lowest = F.lowest_hp_ally(engine, actor.owner_id)
        lowest_r = F.hp_ratio(lowest) if lowest else 1.0

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            if energy <= 2:
                return 80.0
            if energy <= 4 and lowest_r > 0.55:
                return 35.0
            return 0.0

        if at == ActionType.normal_attack.value:
            enemy = engine.find_spirit_anywhere(action.get("targetId") or "")
            if not enemy:
                return 5.0
            # Prefer chip when nobody needs care and energy is tight.
            score = 15.0 + (1.0 - F.hp_ratio(enemy)) * 20.0
            if energy <= 1:
                score += 10.0
            if lowest_r < 0.5:
                score -= 25.0
            return score

        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        tid = action.get("targetId")
        target = engine.find_spirit_anywhere(tid) if tid else None

        if skill_id == "flora_skill1":  # 光合作用
            if not target:
                return -50.0
            r = F.hp_ratio(target)
            score = 30.0 + (1.0 - r) * 120.0
            if r < 0.35:
                score += 40.0
            if r > 0.85:
                score -= 40.0
            # Prefer healing the most injured ally when multiple candidates exist.
            if lowest and target.unique_id == lowest.unique_id:
                score += 15.0
            return score

        if skill_id == "flora_skill2":  # 抗逆
            if not target:
                return -50.0
            r = F.hp_ratio(target)
            score = 20.0 + (1.0 - r) * 50.0
            if r < 0.45:
                score += 25.0
            if r > 0.75:
                score -= 20.0
            if lowest and target.unique_id == lowest.unique_id:
                score += 10.0
            return score

        if skill_id == "flora_skill3":  # 麻醉
            score = 28.0
            if lowest_r < 0.4:
                score -= 30.0
            if energy >= 6:
                score += 10.0
            return score

        return 0.0
