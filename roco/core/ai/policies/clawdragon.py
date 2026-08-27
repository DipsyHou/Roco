"""上古战龙 AI."""

from __future__ import annotations

from typing import Any, Dict

from ...battle.engine import BattleEngine
from ...battle.types import ActionType, BattleSpirit, EffectType
from .. import features as F


def _has_dance(actor: BattleSpirit) -> bool:
    return any(
        e.type == EffectType.buff_stat_percent_boost and e.source_id == actor.unique_id
        for e in actor.effects
    )


class ClawdragonPolicy:
    template_id = "clawdragon"

    def score(
        self,
        engine: BattleEngine,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> float:
        at = action.get("type")
        energy = F.team_energy(engine, actor.owner_id)
        danced = _has_dance(actor)
        focus = F.lowest_hp_enemy(engine, actor.owner_id)

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            if energy < 3:
                return 140.0
            if energy < 5 and not danced:
                return 60.0
            return 10.0

        if at == ActionType.normal_attack.value:
            enemy = engine.find_spirit_anywhere(action.get("targetId") or "")
            if not enemy:
                return 5.0
            score = 25.0 + (1.0 - F.hp_ratio(enemy)) * 20.0
            if focus and enemy.unique_id == focus.unique_id:
                score += 10.0
            if danced:
                score += 10.0
            return score

        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        tid = action.get("targetId")
        target = engine.find_spirit_anywhere(tid) if tid else None

        if skill_id == "clawdragon_skill2":  # 龙之舞
            if danced:
                return -10.0
            return 155.0 if energy >= 3 else 20.0

        if skill_id == "clawdragon_skill1":  # 传说力量
            if not target:
                return -50.0
            score = 90.0 + (1.0 - F.hp_ratio(target)) * 50.0
            if focus and target.unique_id == focus.unique_id:
                score += 15.0
            if danced:
                score += 15.0
            return score

        if skill_id == "clawdragon_skill3":  # 过肩摔
            if not target:
                return -50.0
            score = 105.0 + (1.0 - F.hp_ratio(target)) * 65.0
            if focus and target.unique_id == focus.unique_id:
                score += 20.0
            if danced:
                score += 10.0
            if energy < 4:
                score -= 40.0
            return score

        return 0.0
