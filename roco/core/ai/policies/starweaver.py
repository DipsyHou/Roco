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
        energy = F.team_energy(engine, actor.owner_id)
        needy = F.ally_with_most_debuffs(engine, actor.owner_id)
        focus = F.lowest_hp_enemy(engine, actor.owner_id)

        if at == ActionType.skip.value:
            return -100.0
        # 黑猫技能不吃队伍能量；聚能只在队费极低时给队友让路。
        if at == ActionType.gather_energy.value:
            return 25.0 if energy <= 1 else -5.0

        if at == ActionType.normal_attack.value:
            enemy = engine.find_spirit_anywhere(action.get("targetId") or "")
            if not enemy:
                return 5.0
            score = 12.0 + (1.0 - F.hp_ratio(enemy)) * 20.0
            if pe >= 4:
                score -= 15.0  # prefer spending 秘能 skills
            if focus and enemy.unique_id == focus.unique_id:
                score += 8.0
            return score

        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        tid = action.get("targetId")
        target = engine.find_spirit_anywhere(tid) if tid else None

        if skill_id == "starweaver_skill1":  # 汲取
            score = 40.0
            if pe <= 3:
                score += 35.0
            if pe >= 7:
                score -= 10.0
            return score

        if skill_id == "starweaver_skill2":  # 净化
            if not target:
                return -50.0
            n = F.debuff_count(target)
            score = 20.0 + n * 35.0
            if n <= 0:
                score -= 40.0
            if needy and target.unique_id == needy.unique_id:
                score += 20.0
            if pe < 4:
                score -= 80.0
            return score

        if skill_id == "starweaver_skill3":  # 星爆
            score = 15.0 + pe * 12.0
            if pe < 4:
                score -= 30.0
            if pe >= 6:
                score += 25.0
            # Avoid early suicide stun if team is already collapsing.
            lowest = F.lowest_hp_ally(engine, actor.owner_id)
            if lowest and F.hp_ratio(lowest) < 0.25:
                score -= 20.0
            return score

        return 0.0
