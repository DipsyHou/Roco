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
                return 85.0
            if energy < 4 and burns < 8:
                return 40.0
            return 5.0

        if at == ActionType.normal_attack.value:
            enemy = engine.find_spirit_anywhere(action.get("targetId") or "")
            if not enemy:
                return 5.0
            score = 22.0 + (1.0 - F.hp_ratio(enemy)) * 20.0
            # AA applies warmup burns — prefer already-burning or focus target.
            score += get_total_burn_stacks(enemy) * 3.0
            if focus and enemy.unique_id == focus.unique_id:
                score += 12.0
            if warmup >= 4:
                score += 15.0
            if energy <= 1:
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
            score = 55.0 + (1.0 - F.hp_ratio(target)) * 15.0
            score += get_total_burn_stacks(target) * 2.0
            if focus and target.unique_id == focus.unique_id:
                score += 18.0
            if warmup >= 2:
                score += 10.0
            return score

        if skill_id == "steamdragon_skill2":  # 嗜热
            score = 10.0 + burns * 4.0
            if self_r < 0.55:
                score += 35.0
            if self_r > 0.85:
                score -= 25.0
            if burns < 5:
                score -= 20.0
            return score

        if skill_id == "steamdragon_skill3":  # 沸腾
            score = 35.0
            if warmup >= 8:
                score -= 25.0
            if self_r < 0.35:
                score -= 40.0
            if burns < 3 and warmup < 4:
                score += 20.0  # need fuel for spreading
            return score

        return 0.0
