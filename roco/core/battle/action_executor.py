"""Action execution (normal attack / skill / gather / skip), split from engine.

Resolves the *effect* of a submitted action. Turn sequencing, timeline, and
energy accounting live elsewhere; this module only performs the action itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .damage import calculate_damage
from .events import DamageSource
from .hp import apply_damage
from .rules import TEAM_GATHER_ENERGY_GAIN
from .stats import get_effective_stat
from .types import (
    ActionType,
    BattleLogType,
    BattleSpirit,
    DamageType,
    StatType,
    TargetType,
)
from . import messages as msg
from ..spirits import get_spirit_logic, get_spirit_template

if TYPE_CHECKING:
    from .engine import BattleEngine


class ActionExecutor:
    def __init__(self, engine: "BattleEngine") -> None:
        self._eng = engine

    def execute_action(self, player_id: str, action: Dict[str, Any]) -> None:
        eng = self._eng
        at = action.get("type")
        if at == ActionType.normal_attack.value:
            # 发动目标在出手前快照；通知（含共振等附加伤害）在伤害段之后。
            launch_targets = self._snapshot_attack_launch_targets(player_id, action)
            self.execute_normal_attack_impl(player_id, action, False)
            self._notify_attack_launch(player_id, action, launch_targets)
            self._notify_sole_target(player_id, action)
            self._notify_ally_action(player_id, action)
        elif at == ActionType.use_skill.value:
            launch_targets = self._snapshot_attack_launch_targets(player_id, action)
            self.execute_skill(player_id, action)
            self._notify_attack_launch(player_id, action, launch_targets)
            self._notify_sole_target(player_id, action)
            self._notify_ally_action(player_id, action)
        elif at == ActionType.gather_energy.value:
            actor = eng.find_spirit(player_id, action.get("actorId") or "")
            name = actor.name if actor else "未知精灵"
            eng.add_log(
                BattleLogType.action_executed,
                msg.used_gather(name),
                {"actorId": actor.unique_id if actor else None, "playerId": player_id},
            )
            eng._energy.gain(player_id, TEAM_GATHER_ENERGY_GAIN)
        elif at == ActionType.skip.value:
            actor = eng.find_spirit(player_id, action.get("actorId") or "")
            name = actor.name if actor else "未知精灵"
            eng.add_log(
                BattleLogType.action_executed,
                msg.skipped_action(name),
                {"actorId": actor.unique_id if actor else None, "playerId": player_id},
            )

    def _enemy_attack_targets(
        self, actor: BattleSpirit, action: Dict[str, Any]
    ) -> Optional[List[BattleSpirit]]:
        """Enemy targets if this action launches an attack; else ``None``."""
        eng = self._eng
        at = action.get("type")
        opponent_id = eng.get_opponent_id(actor.owner_id)

        if at == ActionType.normal_attack.value:
            target = eng.find_spirit_anywhere(action.get("targetId") or "")
            if target and target.is_alive and target.owner_id == opponent_id:
                return [target]
            return None

        if at != ActionType.use_skill.value:
            return None
        sk = action.get("skillId")
        tpl = get_spirit_template(actor.template_id)
        if not tpl or not sk:
            return None
        skill = next((s for s in tpl.skills if s.id == sk), None)
        if not skill:
            return None
        logic = get_spirit_logic(actor.template_id)
        if logic:
            launch_override = logic.get_attack_launch_targets(eng, actor, action, skill)
            if launch_override is not None:
                return launch_override or None
        # 无伤害倍率（未声明 launches_attack）的技能不算发动攻击，即使目标是敌方。
        if not skill.launches_attack:
            return None
        tt = skill.target_type
        if logic:
            override = logic.get_skill_target_type(eng, actor, skill)
            if override is not None:
                tt = override

        if tt == TargetType.all_enemies:
            enemies = [s for s in eng.get_active_spirits(opponent_id) if s.is_alive]
            return enemies or None
        if tt == TargetType.single_enemy:
            target = eng.find_spirit_anywhere(action.get("targetId") or "")
            if target and target.is_alive and target.owner_id == opponent_id:
                return [target]
            return None
        # any_on_field 等：默认无明确敌方目标列表；牌面等特例走 get_attack_launch_targets。
        return None

    def _snapshot_attack_launch_targets(
        self, player_id: str, action: Dict[str, Any]
    ) -> Optional[List[BattleSpirit]]:
        """Resolve launch targets before damage so KO mid-action does not erase the list."""
        eng = self._eng
        actor = eng.find_spirit(player_id, action.get("actorId") or "")
        if not actor or not actor.is_alive:
            return None
        return self._enemy_attack_targets(actor, action)

    def _notify_attack_launch(
        self,
        player_id: str,
        action: Dict[str, Any],
        targets: Optional[List[BattleSpirit]],
    ) -> None:
        """Broadcast 发动攻击 once after the action's own damage segments."""
        eng = self._eng
        actor = eng.find_spirit(player_id, action.get("actorId") or "")
        if not actor or not actor.is_alive:
            return
        if not targets:
            return
        logic = get_spirit_logic(actor.template_id)
        if logic:
            logic.on_attack(eng, actor, action, targets)
        for spirit in eng.get_all_spirits(player_id):
            if not spirit.is_alive or spirit.unique_id == actor.unique_id:
                continue
            ally_logic = get_spirit_logic(spirit.template_id)
            if ally_logic:
                ally_logic.on_ally_attack(eng, spirit, actor, action, targets)

    def _notify_ally_action(self, player_id: str, action: Dict[str, Any]) -> None:
        eng = self._eng
        actor = eng.find_spirit(player_id, action.get("actorId") or "")
        if not actor or not actor.is_alive:
            return
        for spirit in eng.get_all_spirits(player_id):
            if not spirit.is_alive or spirit.unique_id == actor.unique_id:
                continue
            logic = get_spirit_logic(spirit.template_id)
            if logic:
                logic.on_ally_action(eng, spirit, actor, action)

    def _resolve_sole_target(
        self, player_id: str, action: Dict[str, Any]
    ) -> Optional[BattleSpirit]:
        """The single designated target of a NA/skill, if any.

        AOE / no-target skills return ``None``. Self skills count as the actor.
        """
        eng = self._eng
        actor = eng.find_spirit(player_id, action.get("actorId") or "")
        if not actor:
            return None
        at = action.get("type")
        if at == ActionType.normal_attack.value:
            target = eng.find_spirit_anywhere(action.get("targetId") or "")
            if target and target.is_alive:
                return target
            return None
        if at != ActionType.use_skill.value:
            return None
        sk = action.get("skillId")
        tpl = get_spirit_template(actor.template_id)
        if not tpl or not sk:
            return None
        skill = next((s for s in tpl.skills if s.id == sk), None)
        if not skill:
            return None
        tt = skill.target_type
        logic = get_spirit_logic(actor.template_id)
        if logic:
            override = logic.get_skill_target_type(eng, actor, skill)
            if override is not None:
                tt = override
        if tt == TargetType.self:
            return actor if actor.is_alive else None
        if tt in (
            TargetType.single_enemy,
            TargetType.single_ally,
            TargetType.single_ally_on_field,
            TargetType.any_on_field,
        ):
            target = eng.find_spirit_anywhere(action.get("targetId") or "")
            if target and target.is_alive:
                return target
        return None

    def _notify_sole_target(self, player_id: str, action: Dict[str, Any]) -> None:
        eng = self._eng
        sole = self._resolve_sole_target(player_id, action)
        if not sole or not sole.is_alive:
            return
        logic = get_spirit_logic(sole.template_id)
        if logic:
            logic.on_became_sole_target(eng, sole, action)

    def execute_normal_attack_impl(
        self,
        player_id: str,
        action: Dict[str, Any],
        is_auto_triggered: bool,
    ) -> None:
        eng = self._eng
        actor = eng.find_spirit(player_id, action.get("actorId") or "")
        if not actor or not actor.is_alive:
            return

        logic = get_spirit_logic(actor.template_id)
        if logic and logic.execute_normal_attack(eng, player_id, actor, action):
            return

        targets = self._resolve_targets(actor, action, is_auto_triggered)
        if not targets:
            return

        primary = targets[0]
        for target in targets:
            if target.is_alive:
                self._apply_hit(actor, target)

        if primary.is_alive:
            actor.last_attack_target_id = primary.unique_id

    def _apply_hit(self, actor: BattleSpirit, target: BattleSpirit) -> None:
        eng = self._eng
        atk = get_effective_stat(actor, StatType.atk)
        phys = calculate_damage(atk, DamageType.physical, actor, target)
        actual = apply_damage(target, phys, ctx=eng)
        eng.add_log(
            BattleLogType.damage_dealt,
            msg.physical_hit(actor.name, target.name, actual),
            {"attackerId": actor.unique_id, "targetId": target.unique_id, "damage": actual},
        )
        eng.notify_damage_taken(actor, target, actual, source=DamageSource.attack)
        if not target.is_alive:
            eng.add_log(
                BattleLogType.spirit_defeated,
                msg.defeated(target.name),
                {"targetId": target.unique_id},
            )

    def _resolve_targets(
        self,
        actor: BattleSpirit,
        action: Dict[str, Any],
        is_auto_triggered: bool,
    ) -> List[BattleSpirit]:
        eng = self._eng
        opponent_id = eng.get_opponent_id(actor.owner_id)
        t = eng.find_spirit_anywhere(action.get("targetId") or "")
        if t and t.is_alive and t.owner_id == opponent_id:
            return [t]

        if is_auto_triggered and actor.last_attack_target_id:
            last = eng.find_spirit_anywhere(actor.last_attack_target_id)
            if last and last.is_alive and last.owner_id == opponent_id:
                return [last]

        enemies = eng.get_active_spirits(opponent_id)
        if not enemies:
            return []
        return [eng.next_rng("auto_target", actor.unique_id).choice(enemies)]

    def execute_skill(self, player_id: str, action: Dict[str, Any]) -> None:
        eng = self._eng
        actor = eng.find_spirit(player_id, action.get("actorId") or "")
        if not actor or not actor.is_alive:
            return
        tpl = get_spirit_template(actor.template_id)
        if not tpl:
            return
        sk = action.get("skillId")
        skill = next((s for s in tpl.skills if s.id == sk), None)
        if not skill:
            return

        logic = get_spirit_logic(actor.template_id)
        if not (logic and logic.suppress_skill_use_log(actor, skill)):
            eng.add_log(
                BattleLogType.action_executed,
                msg.used_skill(actor.name, skill.name),
                {"actorId": actor.unique_id, "skillId": skill.id},
            )

        if logic:
            if logic.should_use_team_energy(actor, skill):
                eng._energy.spend(player_id, actor, skill)
            logic.consume_skill_resources(actor, skill)
            logic.execute_skill(eng, player_id, actor, action)
