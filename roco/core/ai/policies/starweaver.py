"""黑猫巫师 AI."""

from __future__ import annotations

from typing import Any, Dict

from ...battle.engine import BattleEngine
from ...battle.types import ActionType, BattleSpirit
from .. import features as F


class StarweaverPolicy:
    template_id = "starweaver"

    def score(
        self,
        engine: BattleEngine,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> float:
        at = action.get("type")
        pe = actor.energy or 0
        team_energy = F.team_energy(engine, actor.owner_id)
        needy = F.ally_with_most_debuffs(engine, actor.owner_id)
        focus = F.lowest_hp_enemy(engine, actor.owner_id)
        lowest_ally = F.lowest_hp_ally(engine, actor.owner_id)

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            if team_energy <= 1 and pe < 4:
                return 80.0
            return 5.0

        if at == ActionType.normal_attack.value:
            enemy = engine.find_spirit_anywhere(action.get("targetId") or "")
            if not enemy:
                return 5.0
            score = 15.0 + (1.0 - F.hp_ratio(enemy)) * 20.0
            if focus and enemy.unique_id == focus.unique_id:
                score += 10.0
            if pe >= 4:
                score -= 10.0
            return score

        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        tid = action.get("targetId")
        target = engine.find_spirit_anywhere(tid) if tid else None

        if skill_id == "starweaver_skill1":  # 汲取
            score = 120.0
            if pe <= 3:
                score += 40.0
            if team_energy <= 2:
                score += 10.0
            return score

        if skill_id == "starweaver_skill2":  # 净化
            if not target:
                return -50.0
            n = F.debuff_count(target)
            if n <= 0:
                return -40.0
            score = 130.0 + n * 30.0
            if needy and target.unique_id == needy.unique_id:
                score += 20.0
            if pe < 4:
                score -= 80.0
            return score

        if skill_id == "starweaver_skill3":  # 星爆
            score = 35.0 + pe * 12.0
            if pe < 4:
                score -= 40.0
            if pe >= 7:
                score += 35.0
            if lowest_ally and F.hp_ratio(lowest_ally) < 0.25:
                score -= 15.0
            return score

        return 0.0
