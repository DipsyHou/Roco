"""蒸汽神龙 AI."""

from __future__ import annotations

from typing import Any, Dict

from ...battle.effects import get_total_burn_stacks, get_warmup_stacks
from ...battle.engine import BattleEngine
from ...battle.types import ActionType, BattleSpirit
from .. import features as F


class SteamdragonPolicy:
    template_id = "steamdragon"

    def score(
        self,
        engine: BattleEngine,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> float:
        at = action.get("type")
        energy = F.team_energy(engine, actor.owner_id)
        burns = F.enemy_burn_total(engine, actor.owner_id)
        warmup = get_warmup_stacks(actor)
        self_r = F.hp_ratio(actor)
        focus = F.pick_burn_target(engine, actor.owner_id)

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            if energy < 2:
                return 130.0
            if energy < 4:
                return 45.0
            return 10.0

        if at == ActionType.normal_attack.value:
            enemy = engine.find_spirit_anywhere(action.get("targetId") or "")
            if not enemy:
                return 5.0
            score = 30.0 + (1.0 - F.hp_ratio(enemy)) * 20.0
            score += get_total_burn_stacks(enemy) * 4.0
            if focus and enemy.unique_id == focus.unique_id:
                score += 10.0
            if warmup >= 4:
                score += 10.0
            return score

        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        tid = action.get("targetId")
        target = engine.find_spirit_anywhere(tid) if tid else None

        if skill_id == "steamdragon_skill1":  # 烙印
            if not target:
                return -50.0
            score = 145.0 + (1.0 - F.hp_ratio(target)) * 25.0
            score += get_total_burn_stacks(target) * 3.0
            if focus and target.unique_id == focus.unique_id:
                score += 15.0
            return score

        if skill_id == "steamdragon_skill2":  # 嗜热
            score = 70.0 + burns * 8.0
            if self_r < 0.6:
                score += 35.0
            if burns < 3:
                score -= 20.0
            return score

        if skill_id == "steamdragon_skill3":  # 沸腾
            score = 55.0
            if warmup <= 2 and self_r > 0.5:
                score += 40.0
            if warmup <= 4 and self_r > 0.65:
                score += 15.0
            if self_r < 0.4:
                score -= 40.0
            return score

        return 0.0
