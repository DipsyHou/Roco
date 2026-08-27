"""Simple rule-based AI policies for the remaining spirits."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...battle.engine import BattleEngine
from ...battle.status_effects import (
    count_buff_effects,
    get_freeze_stacks,
    get_poison_stacks,
    get_total_burn_stacks,
    get_warmup_stacks,
)
from ...battle.effect_meta import stack_count
from ...battle.types import ActionType, BattleSpirit, EffectType, StatType
from ...battle.utils import get_state_stack_count
from .. import features as F
from ...spirits.guifashi_cards import TAROT_CARDS
from ...spirits.guifashi_support import get_cards
from ...spirits.tengjiao_state import committed_dish, huoli_stacks, pending_free
from ...spirits.xiaozong import get_lingqi_stacks, has_tongling


ALLY_WORTHY_CARDS = {"star", "tower", "chariot", "hermit"}
ENEMY_WORTHY_CARDS = {"temperance", "judgment"}
CARD_PRIORITY = {
    "fool": 1,
    "demon": 2,
    "moon": 3,
    "sun": 4,
    "temperance": 4,
    "hermit": 5,
    "chariot": 5,
    "tower": 5,
    "star": 6,
    "death": 7,
    "judgment": 8,
}
DISH_NAMES = {"辣子鸡", "水煮鱼", "毛血旺"}


def _target(engine: BattleEngine, target_id: str | None) -> Optional[BattleSpirit]:
    if not target_id:
        return None
    return engine.find_spirit_anywhere(target_id)


def _enemy_target(
    engine: BattleEngine,
    player_id: str,
    action: Dict[str, Any],
) -> Optional[BattleSpirit]:
    target = _target(engine, action.get("targetId"))
    if not target or not target.is_alive:
        return None
    return target if target.owner_id == engine.get_opponent_id(player_id) else None


def _ally_target(
    engine: BattleEngine,
    player_id: str,
    action: Dict[str, Any],
) -> Optional[BattleSpirit]:
    target = _target(engine, action.get("targetId"))
    if not target or not target.is_alive:
        return None
    return target if target.owner_id == player_id else None


def _effect_count(
    spirit: BattleSpirit,
    effect_type: EffectType,
    *,
    source_id: str | None = None,
    display_name: str | None = None,
) -> int:
    count = 0
    for effect in spirit.effects:
        if effect.type != effect_type:
            continue
        if source_id is not None and effect.source_id != source_id:
            continue
        if display_name is not None and effect.display_name != display_name:
            continue
        count += 1
    return count


def _has_display_name(spirit: BattleSpirit, name: str) -> bool:
    return any(effect.display_name == name for effect in spirit.effects)


def _has_effect(spirit: BattleSpirit, effect_type: EffectType) -> bool:
    return any(effect.type == effect_type for effect in spirit.effects)


def _enemy_count(engine: BattleEngine, player_id: str) -> int:
    return len(F.enemies(engine, player_id))


def _ally_count(engine: BattleEngine, player_id: str) -> int:
    return len(F.allies(engine, player_id))


def _main_c_enemy(engine: BattleEngine, player_id: str) -> Optional[BattleSpirit]:
    return F.main_c_ally(engine, engine.get_opponent_id(player_id))


def _best_poison_target(engine: BattleEngine, player_id: str) -> Optional[BattleSpirit]:
    pool = F.enemies(engine, player_id)
    if not pool:
        return None
    return max(pool, key=lambda s: (get_poison_stacks(s), -s.current_hp, -s.slot))


def _best_burn_target(engine: BattleEngine, player_id: str) -> Optional[BattleSpirit]:
    pool = F.enemies(engine, player_id)
    if not pool:
        return None
    return max(pool, key=lambda s: (get_total_burn_stacks(s), -s.current_hp, -s.slot))


def _highest_flaw_target(engine: BattleEngine, player_id: str) -> Optional[BattleSpirit]:
    pool = F.enemies(engine, player_id)
    if not pool:
        return None
    return max(
        pool,
        key=lambda s: (
            _effect_count(s, EffectType.debuff_flaw),
            -s.current_hp,
            -s.slot,
            -s.unique_id.__hash__(),
        ),
    )


def _best_dish_action_score(action: Dict[str, Any]) -> float:
    if action.get("targetId"):
        return 1.0
    return 0.0


class ParsasPolicy:
    template_id = "parsas"

    def score(self, engine: BattleEngine, actor: BattleSpirit, action: Dict[str, Any]) -> float:
        at = action.get("type")
        energy = actor.energy or 0
        focus = F.lowest_hp_enemy_with_tiebreak(engine, actor.owner_id)

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            return 35.0 if energy < 3 else 8.0
        if at == ActionType.normal_attack.value:
            target = _enemy_target(engine, actor.owner_id, action)
            if not target:
                return 5.0
            score = 30.0 + (1.0 - F.hp_ratio(target)) * 18.0
            if energy < 13:
                score += 8.0
            if focus and target.unique_id == focus.unique_id:
                score += 8.0
            return score
        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        target = _enemy_target(engine, actor.owner_id, action)

        if skill_id == "parsas_skill1":
            if F.hp_ratio(actor) < 0.25:
                return -40.0
            score = 120.0 if energy < 13 else 60.0
            if energy < 7:
                score += 20.0
            return score
        if skill_id == "parsas_skill2":
            if energy < 7:
                return -50.0
            score = 130.0
            if target:
                score += (1.0 - F.hp_ratio(target)) * 25.0
                if focus and target.unique_id == focus.unique_id:
                    score += 15.0
            return score
        if skill_id == "parsas_skill3":
            if energy < 13:
                return -60.0
            score = 150.0
            if target:
                score += (1.0 - F.hp_ratio(target)) * 30.0
                if focus and target.unique_id == focus.unique_id:
                    score += 20.0
            return score
        return 0.0


class ChaoslingPolicy:
    template_id = "chaosling"

    def _is_channeling(self, actor: BattleSpirit) -> bool:
        return any(
            effect.type == EffectType.state_channeling_skill
            and effect.channel_skill_id == "chaosling_skill1"
            for effect in actor.effects
        )

    def score(self, engine: BattleEngine, actor: BattleSpirit, action: Dict[str, Any]) -> float:
        at = action.get("type")
        energy = F.team_energy(engine, actor.owner_id)
        enemy_count = _enemy_count(engine, actor.owner_id)
        debuffs = F.debuff_count(actor)

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            return 120.0 if energy < 2 else 6.0
        if at == ActionType.normal_attack.value:
            target = _enemy_target(engine, actor.owner_id, action)
            if not target:
                return 5.0
            score = 22.0 + (1.0 - F.hp_ratio(target)) * 16.0
            if enemy_count >= 3:
                score += 6.0
            return score
        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        target = _enemy_target(engine, actor.owner_id, action)

        if skill_id == "chaosling_skill1":
            if self._is_channeling(actor):
                return -20.0
            score = 145.0 if energy >= 3 else 15.0
            if enemy_count >= 2:
                score += 10.0
            return score
        if skill_id == "chaosling_skill2":
            if energy < 2:
                return -40.0
            score = 130.0 + enemy_count * 6.0
            if debuffs <= 0:
                score -= 10.0
            return score
        if skill_id == "chaosling_skill3":
            if energy < 4:
                return -50.0
            score = 110.0
            if debuffs > 0:
                score += 45.0
            if target:
                score += (1.0 - F.hp_ratio(target)) * 15.0
            return score
        return 0.0


class QiukaPolicy:
    template_id = "qiuka"

    def score(self, engine: BattleEngine, actor: BattleSpirit, action: Dict[str, Any]) -> float:
        at = action.get("type")
        energy = F.team_energy(engine, actor.owner_id)
        enemy_count = _enemy_count(engine, actor.owner_id)
        target = _enemy_target(engine, actor.owner_id, action)
        poison = get_poison_stacks(target) if target else 0

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            return 110.0 if energy < 2 else 5.0
        if at == ActionType.normal_attack.value:
            if not target:
                return 5.0
            score = 28.0 + (1.0 - F.hp_ratio(target)) * 18.0 + poison * 6.0
            return score
        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")

        if skill_id == "qiuka_skill1":
            if energy < 3:
                return -40.0
            score = 130.0
            if enemy_count >= 3:
                score += 20.0
            elif enemy_count == 2:
                score += 10.0
            return score
        if skill_id == "qiuka_skill2":
            if energy < 2:
                return -40.0
            score = 120.0
            if target:
                score += poison * 8.0
                score += (1.0 - F.hp_ratio(target)) * 18.0
            return score
        if skill_id == "qiuka_skill3":
            if energy < 3:
                return -40.0
            score = 125.0
            if poison > 0:
                score += 30.0 + poison * 8.0
            if target:
                score += (1.0 - F.hp_ratio(target)) * 25.0
            return score
        return 0.0


class FanyingPolicy:
    template_id = "fanying"

    def _wing_guard_count(self, actor: BattleSpirit, target: BattleSpirit) -> int:
        return _effect_count(
            target,
            EffectType.state_wing_guard,
            source_id=actor.unique_id,
        )

    def score(self, engine: BattleEngine, actor: BattleSpirit, action: Dict[str, Any]) -> float:
        at = action.get("type")
        energy = F.team_energy(engine, actor.owner_id)
        main_c = F.main_c_ally(engine, actor.owner_id)
        lowest_ally = F.lowest_hp_ally(engine, actor.owner_id)

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            return 110.0 if energy < 2 else 4.0
        if at == ActionType.normal_attack.value:
            target = _enemy_target(engine, actor.owner_id, action)
            if not target:
                return 5.0
            score = 24.0 + (1.0 - F.hp_ratio(target)) * 18.0
            return score
        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        target = _target(engine, action.get("targetId"))

        if skill_id == "fanying_skill1":
            if energy < 1:
                return -30.0
            if not target or target.owner_id == actor.owner_id:
                return -20.0
            score = 110.0 + (1.0 - F.hp_ratio(target)) * 18.0
            if _effect_count(target, EffectType.debuff_stat_percent_reduction, source_id=actor.unique_id, display_name="气旋") > 0:
                score += 10.0
            return score

        if skill_id == "fanying_skill2":
            if energy < 2:
                return -40.0
            if not target or target.owner_id != actor.owner_id:
                return -20.0
            score = 130.0
            if main_c and target.unique_id == main_c.unique_id:
                score += 20.0
            elif lowest_ally and target.unique_id == lowest_ally.unique_id:
                score += 10.0
            if self._wing_guard_count(actor, target) > 0:
                score -= 15.0
            return score

        if skill_id == "fanying_skill3":
            if energy < 3:
                return -50.0
            if not target:
                return -20.0
            if target.owner_id == actor.owner_id:
                score = 150.0
                if main_c and target.unique_id == main_c.unique_id:
                    score += 25.0
                elif lowest_ally and target.unique_id == lowest_ally.unique_id:
                    score += 10.0
                return score
            score = 95.0 + (1.0 - F.hp_ratio(target)) * 20.0
            if F.hp_ratio(target) < 0.5:
                score += 15.0
            return score
        return 0.0


class CuidingPolicy:
    template_id = "cuiding"

    def score(self, engine: BattleEngine, actor: BattleSpirit, action: Dict[str, Any]) -> float:
        at = action.get("type")
        energy = F.team_energy(engine, actor.owner_id)
        lowest_ally = F.lowest_hp_ally(engine, actor.owner_id)
        main_c = F.main_c_ally(engine, actor.owner_id)
        low_allies = [ally for ally in F.allies(engine, actor.owner_id) if F.hp_ratio(ally) < 0.75]

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            return 110.0 if energy < 3 else 5.0
        if at == ActionType.normal_attack.value:
            target = _enemy_target(engine, actor.owner_id, action)
            if not target:
                return 5.0
            return 18.0 + (1.0 - F.hp_ratio(target)) * 15.0
        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        target = _ally_target(engine, actor.owner_id, action)

        if skill_id == "cuiding_skill1":
            if energy < 3:
                return -40.0
            if not target:
                return -20.0
            score = 130.0 + (1.0 - F.hp_ratio(target)) * 45.0
            if main_c and target.unique_id == main_c.unique_id:
                score += 15.0
            if target in low_allies:
                score += 10.0
            return score

        if skill_id == "cuiding_skill2":
            if energy < 3:
                return -40.0
            score = 100.0
            enemy = _enemy_target(engine, actor.owner_id, action)
            if enemy:
                score += (1.0 - F.hp_ratio(enemy)) * 20.0
                score += count_buff_effects(enemy) * 8.0
            if len(low_allies) == 0:
                score += 20.0
            return score

        if skill_id == "cuiding_skill3":
            if energy < 5:
                return -50.0
            score = 90.0
            if len(low_allies) >= 2:
                score += 40.0
            if lowest_ally and F.hp_ratio(lowest_ally) < 0.5:
                score += 30.0
            if main_c and F.hp_ratio(main_c) < 0.7:
                score += 15.0
            return score
        return 0.0


class TitaPolicy:
    template_id = "tita"

    def score(self, engine: BattleEngine, actor: BattleSpirit, action: Dict[str, Any]) -> float:
        at = action.get("type")
        energy = F.team_energy(engine, actor.owner_id)
        shunt = get_state_stack_count(actor, EffectType.state_shunt)
        expansion = get_state_stack_count(actor, EffectType.state_expansion)
        target = _enemy_target(engine, actor.owner_id, action)
        enemy_lowest = F.lowest_hp_enemy_with_tiebreak(engine, actor.owner_id)

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            return 140.0 if energy < 3 else 4.0
        if at == ActionType.normal_attack.value:
            if not target:
                return 2.0
            return 8.0 + (1.0 - F.hp_ratio(target)) * 8.0
        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        if skill_id == "tita_skill2":
            if energy < 5:
                return -50.0
            if expansion >= 5:
                return 20.0
            score = 150.0 + expansion * 10.0
            if energy >= 7:
                score += 10.0
            return score
        if skill_id == "tita_skill1":
            if energy < 5:
                return -50.0
            if shunt >= 2:
                return 35.0
            score = 140.0
            if expansion >= 3:
                score += 10.0
            return score
        if skill_id == "tita_skill3":
            if energy < 3:
                return -60.0
            if not target:
                return -20.0
            score = 115.0 + (1.0 - F.hp_ratio(target)) * 30.0
            if enemy_lowest and target.unique_id == enemy_lowest.unique_id:
                score += 15.0
            if F.hp_ratio(actor) < 0.5:
                score += 5.0
            return score
        return 0.0


class GuaguaPolicy:
    template_id = "guagua"

    def _master(self, engine: BattleEngine, player_id: str) -> Optional[BattleSpirit]:
        for ally in F.allies(engine, player_id):
            if _effect_count(ally, EffectType.state_shifu) > 0:
                return ally
        return None

    def score(self, engine: BattleEngine, actor: BattleSpirit, action: Dict[str, Any]) -> float:
        at = action.get("type")
        energy = F.team_energy(engine, actor.owner_id)
        main_c = F.main_c_ally(engine, actor.owner_id)
        master = self._master(engine, actor.owner_id)

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            return 120.0 if energy < 2 else 5.0
        if at == ActionType.normal_attack.value:
            target = _enemy_target(engine, actor.owner_id, action)
            if not target:
                return 5.0
            return 26.0 + (1.0 - F.hp_ratio(target)) * 18.0
        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        target = _target(engine, action.get("targetId"))

        if skill_id == "guagua_skill1":
            if energy < 2:
                return -40.0
            if not target or target.owner_id != actor.owner_id or target.unique_id == actor.unique_id:
                return -20.0
            score = 140.0
            if main_c and target.unique_id == main_c.unique_id:
                score += 25.0
            if master and master.unique_id == target.unique_id:
                score -= 20.0
            return score

        if skill_id == "guagua_skill2":
            if energy < 2:
                return -40.0
            target = _enemy_target(engine, actor.owner_id, action)
            if not target:
                return -20.0
            score = 115.0 + (1.0 - F.hp_ratio(target)) * 25.0
            if master:
                score += 15.0
            return score

        if skill_id == "guagua_skill3":
            if energy < 3:
                return -50.0
            score = 110.0
            if master:
                score += 30.0
            if main_c and master and main_c.unique_id == master.unique_id:
                score += 10.0
            if F.hp_ratio(actor) < 0.5:
                score -= 10.0
            return score
        return 0.0


class GuifashiPolicy:
    template_id = "guifashi"

    def _hand(self, actor: BattleSpirit) -> List[str]:
        return list(get_cards(actor).hand)

    def _priority(self, card_id: str) -> int:
        return CARD_PRIORITY.get(card_id, 0)

    def score(self, engine: BattleEngine, actor: BattleSpirit, action: Dict[str, Any]) -> float:
        at = action.get("type")
        state = get_cards(actor)
        hand = state.hand
        deck = state.deck
        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            if len(hand) <= 1 and deck:
                return 95.0
            if len(hand) <= 3 and deck:
                return 65.0
            return 5.0
        if at == ActionType.normal_attack.value:
            target = _enemy_target(engine, actor.owner_id, action)
            if not target:
                return 5.0
            return 20.0 + (1.0 - F.hp_ratio(target)) * 15.0
        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        if skill_id == "guifashi_draw":
            if not deck:
                return 0.0
            if len(hand) <= 1:
                return 110.0
            if len(hand) <= 3:
                return 70.0
            return 30.0

        if skill_id == "guifashi_cheat":
            idx = int(action.get("cardHandIndex", 0))
            if idx < 0 or idx >= len(hand):
                return -50.0
            old_card = hand[idx]
            new_card = str(action.get("newCardId") or "")
            if new_card not in TAROT_CARDS:
                return -50.0
            score = 20.0 + self._priority(new_card) * 12.0 - self._priority(old_card) * 5.0
            if new_card in {"judgment", "death", "star"}:
                score += 20.0
            return score

        if skill_id == "guifashi_show":
            idx = int(action.get("cardHandIndex", 0))
            if idx < 0 or idx >= len(hand):
                return -50.0
            card = hand[idx]
            target = _target(engine, action.get("targetId"))
            main_c = _main_c_enemy(engine, actor.owner_id)
            if card == "sun":
                return 65.0
            if card == "moon":
                return 85.0 if (actor.energy or 0) <= 2 else 45.0
            if card == "star":
                if target and target.owner_id == actor.owner_id:
                    score = 125.0 + (1.0 - F.hp_ratio(target)) * 40.0
                    if main_c and target.unique_id == main_c.unique_id:
                        score += 10.0
                    return score
                return 15.0
            if card == "temperance":
                if target and target.owner_id != actor.owner_id:
                    score = 95.0 + count_buff_effects(target) * 10.0
                    if count_buff_effects(target) <= 0:
                        score -= 10.0
                    return score
                return 15.0
            if card == "judgment":
                if target and target.owner_id != actor.owner_id:
                    score = 130.0 + (1.0 - F.hp_ratio(target)) * 35.0
                    if main_c and target.unique_id == main_c.unique_id:
                        score += 12.0
                    return score
                return 20.0
            if card == "tower":
                if target and target.owner_id == actor.owner_id:
                    score = 92.0 + (1.0 - F.hp_ratio(target)) * 20.0
                    if main_c and target.unique_id == main_c.unique_id:
                        score += 20.0
                    return score
                return 18.0
            if card == "chariot":
                if target and target.owner_id == actor.owner_id:
                    score = 92.0 + (1.0 - F.hp_ratio(target)) * 15.0
                    if main_c and target.unique_id == main_c.unique_id:
                        score += 18.0
                    return score
                return 18.0
            if card == "hermit":
                if target and target.owner_id == actor.owner_id:
                    score = 88.0
                    if main_c and target.unique_id == main_c.unique_id:
                        score += 15.0
                    return score
                return 18.0
            if card == "death":
                score = 120.0
                if _enemy_count(engine, actor.owner_id) >= 2:
                    score += 20.0
                if target and target.owner_id != actor.owner_id:
                    score += (1.0 - F.hp_ratio(target)) * 20.0
                return score
            if card == "fool":
                return 55.0 if deck and len(hand) <= 3 else 25.0
            if card == "demon":
                return 70.0 if len(hand) >= 2 else 20.0
            return 0.0
        return 0.0


class BahamutPolicy:
    template_id = "bahamut"

    def score(self, engine: BattleEngine, actor: BattleSpirit, action: Dict[str, Any]) -> float:
        at = action.get("type")
        energy = F.team_energy(engine, actor.owner_id)
        target = _enemy_target(engine, actor.owner_id, action)

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            return 110.0 if energy < 1 else 4.0
        if at == ActionType.normal_attack.value:
            if not target:
                return 5.0
            return 28.0 + (1.0 - F.hp_ratio(target)) * 18.0
        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        if skill_id == "bahamut_skill1":
            if energy < 1:
                return -40.0
            if not target:
                return -20.0
            return 105.0 + (1.0 - F.hp_ratio(target)) * 35.0
        if skill_id == "bahamut_skill2":
            if energy < 1:
                return -40.0
            score = 115.0
            if F.hp_ratio(actor) < 0.5:
                score += 25.0
            return score
        if skill_id == "bahamut_skill3":
            if energy < 3:
                return -60.0
            score = 160.0 if not _has_display_name(actor, "龙之舞") else 40.0
            return score
        if skill_id in {"bahamut_zhaojia_jiequan", "bahamut_zhaojia_fanpu"}:
            return 140.0 if target else -20.0
        return 0.0


class DaermaoPolicy:
    template_id = "daermao"

    def score(self, engine: BattleEngine, actor: BattleSpirit, action: Dict[str, Any]) -> float:
        at = action.get("type")
        energy = F.team_energy(engine, actor.owner_id)
        enemy_count = _enemy_count(engine, actor.owner_id)
        target = _enemy_target(engine, actor.owner_id, action)

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            return 105.0 if energy < 2 else 4.0
        if at == ActionType.normal_attack.value:
            if not target:
                return 5.0
            return 20.0 + (1.0 - F.hp_ratio(target)) * 15.0
        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        if skill_id == "daermao_skill1":
            if energy < 2:
                return -40.0
            if not target:
                return -20.0
            buffs = count_buff_effects(target)
            return 90.0 + buffs * 18.0
        if skill_id == "daermao_skill2":
            if energy < 2:
                return -40.0
            if not target:
                return -20.0
            score = 120.0 + (1.0 - F.hp_ratio(target)) * 20.0
            if enemy_count >= 2:
                score += 15.0
            return score
        if skill_id == "daermao_skill3":
            if energy < 4:
                return -50.0
            if not target:
                return -20.0
            score = 110.0 + (1.0 - F.hp_ratio(target)) * 15.0
            if _effect_count(target, EffectType.debuff_damage_percent_reduction, display_name="萌化") > 0:
                score -= 20.0
            return score
        return 0.0


class HuxianPolicy:
    template_id = "huxian"

    def score(self, engine: BattleEngine, actor: BattleSpirit, action: Dict[str, Any]) -> float:
        at = action.get("type")
        energy = F.team_energy(engine, actor.owner_id)
        target = _enemy_target(engine, actor.owner_id, action)

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            return 100.0 if energy < 2 else 4.0
        if at == ActionType.normal_attack.value:
            if not target:
                return 5.0
            return 24.0 + (1.0 - F.hp_ratio(target)) * 16.0
        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        burn = get_total_burn_stacks(target) if target else 0
        poison = get_poison_stacks(target) if target else 0

        if skill_id == "huxian_skill1":
            if energy < 2:
                return -40.0
            if not target:
                return -20.0
            return 110.0 + (1.0 - F.hp_ratio(target)) * 20.0
        if skill_id == "huxian_skill2":
            if energy < 3:
                return -50.0
            if not target:
                return -20.0
            score = 120.0 + burn * 10.0 + poison * 6.0
            if burn + poison > 0:
                score += 20.0
            return score
        if skill_id == "huxian_skill3":
            if energy < 3:
                return -50.0
            if not target:
                return -20.0
            score = 125.0 + burn * 12.0
            if burn > 0:
                score += 25.0
            if _enemy_count(engine, actor.owner_id) >= 2:
                score += 10.0
            return score
        return 0.0


class ShengyuPolicy:
    template_id = "shengyu"

    def _copyable_debuffs(self, spirit: BattleSpirit) -> int:
        copyable = {
            EffectType.debuff_stat_percent_reduction,
            EffectType.debuff_stat_flat_reduction,
            EffectType.debuff_damage_percent_reduction,
            EffectType.debuff_damage_flat_reduction,
            EffectType.debuff_taken_damage_percent_boost,
            EffectType.debuff_taken_damage_flat_boost,
        }
        return sum(1 for effect in spirit.effects if effect.type in copyable)

    def score(self, engine: BattleEngine, actor: BattleSpirit, action: Dict[str, Any]) -> float:
        at = action.get("type")
        target = _target(engine, action.get("targetId"))
        enemy_main = _main_c_enemy(engine, actor.owner_id)
        enemy_lowest = F.lowest_hp_enemy_with_tiebreak(engine, actor.owner_id)
        allies = F.allies(engine, actor.owner_id)
        wounded_allies = [ally for ally in allies if F.hp_ratio(ally) < 0.75]

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            return 20.0
        if at == ActionType.normal_attack.value:
            if not target:
                return 5.0
            return 16.0 + (1.0 - F.hp_ratio(target)) * 12.0
        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        if skill_id == "shengyu_skill1":
            if (actor.energy or 0) < 2:
                return -40.0
            if not target or target.owner_id != actor.owner_id:
                return -20.0
            score = 130.0 + (1.0 - F.hp_ratio(target)) * 40.0
            if target.energy is not None:
                score += 10.0
            if target in wounded_allies:
                score += 10.0
            return score
        if skill_id == "shengyu_skill2":
            if (actor.energy or 0) < 4:
                return -50.0
            if not target or target.owner_id == actor.owner_id:
                return -20.0
            score = 105.0
            if enemy_main and target.unique_id == enemy_main.unique_id:
                score += 35.0
            if enemy_lowest and target.unique_id == enemy_lowest.unique_id:
                score += 10.0
            return score
        if skill_id == "shengyu_skill3":
            if (actor.energy or 0) < 5:
                return -60.0
            if not target or target.owner_id == actor.owner_id:
                return -20.0
            debuffs = self._copyable_debuffs(target)
            if debuffs <= 0:
                return -30.0
            score = 150.0 + debuffs * 20.0
            if enemy_main and target.unique_id == enemy_main.unique_id:
                score += 15.0
            return score
        return 0.0


class DeerlePolicy:
    template_id = "deerle"

    def _flaw_count(self, spirit: BattleSpirit) -> int:
        return _effect_count(spirit, EffectType.debuff_flaw)

    def _jianwu_stacks(self, actor: BattleSpirit) -> int:
        eff = next((e for e in actor.effects if e.type == EffectType.state_jianwu), None)
        return stack_count(eff) if eff else 0

    def score(self, engine: BattleEngine, actor: BattleSpirit, action: Dict[str, Any]) -> float:
        at = action.get("type")
        energy = F.team_energy(engine, actor.owner_id)
        target = _enemy_target(engine, actor.owner_id, action)
        highest_flaw = _highest_flaw_target(engine, actor.owner_id)

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            return 95.0 if energy < 1 else 4.0
        if at == ActionType.normal_attack.value:
            if not target:
                return 5.0
            flaws = self._flaw_count(target)
            score = 24.0 + (1.0 - F.hp_ratio(target)) * 18.0
            if flaws >= 3:
                score += 40.0 + flaws * 8.0
            return score
        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        if skill_id == "deerle_skill1":
            if energy < 3:
                return -50.0
            stacks = self._jianwu_stacks(actor)
            score = 150.0 if stacks < 3 else 110.0
            if stacks >= 6:
                score -= 30.0
            return score
        if skill_id == "deerle_skill2":
            if energy < 1:
                return -40.0
            if not target:
                return -20.0
            score = 120.0 + (1.0 - F.hp_ratio(target)) * 25.0
            flaws = self._flaw_count(target)
            if flaws > 0:
                score += flaws * 8.0
            if highest_flaw and target.unique_id == highest_flaw.unique_id:
                score += 10.0
            return score
        return 0.0


class TengjiaoPolicy:
    template_id = "tengjiao"

    def _has_dish(self, engine: BattleEngine, player_id: str) -> bool:
        for spirit in F.allies(engine, player_id) + F.enemies(engine, player_id):
            for effect in spirit.effects:
                if effect.display_name in DISH_NAMES:
                    return True
        return False

    def score(self, engine: BattleEngine, actor: BattleSpirit, action: Dict[str, Any]) -> float:
        at = action.get("type")
        energy = F.team_energy(engine, actor.owner_id)
        huoli = huoli_stacks(actor)
        free_pending = pending_free(actor)
        main_c = F.main_c_ally(engine, actor.owner_id)
        target = _target(engine, action.get("targetId"))

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            return 105.0 if energy < 2 else 4.0
        if at == ActionType.normal_attack.value:
            if not target:
                return 5.0
            return 22.0 + (1.0 - F.hp_ratio(target)) * 16.0
        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        if skill_id == "tengjiao_skill1":
            if energy < 2:
                return -40.0
            bonus = 0.0
            after = huoli + 5
            for threshold in (10, 20, 30):
                if huoli < threshold <= after:
                    bonus += 20.0
            return 120.0 + bonus
        if skill_id == "tengjiao_skill2":
            if energy < 2:
                return -40.0
            score = 70.0
            if self._has_dish(engine, actor.owner_id):
                score += 40.0
            return score
        if skill_id == "tengjiao_skill3":
            if free_pending:
                return 210.0
            if target and target.owner_id == actor.owner_id:
                score = 150.0
                if main_c and target.unique_id == main_c.unique_id:
                    score += 20.0
                if F.hp_ratio(target) < 0.7:
                    score += 10.0
                return score
            if not target:
                score = 130.0
                if huoli >= 20:
                    score += 25.0
                if huoli >= 30:
                    score += 10.0
                return score
            score = 125.0 + (1.0 - F.hp_ratio(target)) * 20.0
            return score
        return 0.0


class EmozhanshiPolicy:
    template_id = "emozhanshi"

    def score(self, engine: BattleEngine, actor: BattleSpirit, action: Dict[str, Any]) -> float:
        at = action.get("type")
        target = _enemy_target(engine, actor.owner_id, action)
        enemy_lowest = F.lowest_hp_enemy_with_tiebreak(engine, actor.owner_id)
        enemy_count = _enemy_count(engine, actor.owner_id)
        hp = F.hp_ratio(actor)

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            return 4.0
        if at == ActionType.normal_attack.value:
            if not target:
                return 5.0
            return 20.0 + (1.0 - F.hp_ratio(target)) * 14.0
        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        if skill_id == "emozhanshi_skill1":
            score = 110.0 if hp > 0.6 else 70.0
            if not _has_effect(actor, EffectType.state_roudun):
                score += 20.0
            return score
        if skill_id == "emozhanshi_skill2":
            missing = 1.0 - hp
            score = 90.0 + missing * 80.0
            if missing > 0.25:
                score += 20.0
            return score
        if skill_id == "emozhanshi_skill3":
            if not enemy_lowest:
                return -50.0
            score = 75.0 + hp * 55.0 + (1.0 - F.hp_ratio(enemy_lowest)) * 60.0
            if enemy_count <= 2:
                score += 20.0
            if F.hp_ratio(enemy_lowest) < 0.45:
                score += 20.0
            return score
        return 0.0


class XiaozongPolicy:
    template_id = "xiaozong"

    def score(self, engine: BattleEngine, actor: BattleSpirit, action: Dict[str, Any]) -> float:
        at = action.get("type")
        energy = F.team_energy(engine, actor.owner_id)
        target = _enemy_target(engine, actor.owner_id, action)
        enemy_count = _enemy_count(engine, actor.owner_id)
        lingqi = get_lingqi_stacks(actor)

        if at == ActionType.skip.value:
            return -100.0
        if at == ActionType.gather_energy.value:
            return 100.0 if energy < 3 else 4.0
        if at == ActionType.normal_attack.value:
            if not target:
                return 5.0
            return 22.0 + (1.0 - F.hp_ratio(target)) * 15.0
        if at != ActionType.use_skill.value:
            return 0.0

        skill_id = action.get("skillId")
        if skill_id == "xiaozong_skill3":
            score = 165.0 if not has_tongling(actor) else 95.0
            if F.hp_ratio(actor) < 0.5:
                score -= 10.0
            return score
        if skill_id == "xiaozong_skill1":
            if energy < 3:
                return -50.0
            score = 110.0 + enemy_count * 10.0
            if not has_tongling(actor):
                score += 20.0
            if target:
                score += (1.0 - F.hp_ratio(target)) * 15.0
            return score
        if skill_id == "xiaozong_skill2":
            if energy < 3:
                return -50.0
            if not target:
                return -20.0
            score = 115.0 + lingqi * 1.5 + (1.0 - F.hp_ratio(target)) * 25.0
            if target.unique_id == (F.main_c_ally(engine, actor.owner_id).unique_id if F.main_c_ally(engine, actor.owner_id) else None):
                score += 10.0
            if has_tongling(actor):
                score += 15.0
            return score
        return 0.0


__all__ = [
    "ParsasPolicy",
    "ChaoslingPolicy",
    "QiukaPolicy",
    "FanyingPolicy",
    "CuidingPolicy",
    "GuaguaPolicy",
    "GuifashiPolicy",
    "BahamutPolicy",
    "DaermaoPolicy",
    "HuxianPolicy",
    "ShengyuPolicy",
    "DeerlePolicy",
    "TengjiaoPolicy",
    "EmozhanshiPolicy",
    "XiaozongPolicy",
]
