"""Turn-based battle engine — Python port of server/src/game/BattleEngine.ts."""

from __future__ import annotations

import copy
import random
import uuid
from typing import Any, Dict, List, Optional, Tuple

from .battle_types import (
    ActionType,
    BattleEffect,
    BattleLogEntry,
    BattleLogType,
    BattlePhase,
    BattleSpirit,
    BattleState,
    DamageType,
    EffectType,
    PlayerBattleData,
    StatType,
    SpiritTemplate,
)
from .battle_utils import (
    apply_damage,
    calculate_damage,
    consume_next_damage_reduction,
    get_effective_speed,
    get_effective_stat,
    is_debuff_immune,
    is_stunned,
    make_effect,
    tick_effects,
)
from .spirit_logic import BattleContext
from .spirits import get_spirit_logic, get_spirit_template


def create_battle_spirit(template: SpiritTemplate, owner_id: str) -> BattleSpirit:
    bs = template.base_stats
    spirit = BattleSpirit(
        unique_id=str(uuid.uuid4()),
        template_id=template.id,
        owner_id=owner_id,
        name=template.name,
        base_stats=copy.deepcopy(bs),
        current_hp=bs.hp,
        max_hp=bs.hp,
        effects=[],
        skill_cooldowns={},
        is_on_field=False,
        is_alive=True,
    )
    logic = get_spirit_logic(template.id)
    if logic:
        logic.on_init(spirit)
    return spirit


class BattleEngine(BattleContext):
    def __init__(
        self,
        battle_id: str,
        player1_id: str,
        player2_id: str,
        p1_templates: List[SpiritTemplate],
        p2_templates: List[SpiritTemplate],
    ) -> None:
        self._player_ids = [player1_id, player2_id]
        self.state = BattleState(
            battle_id=battle_id,
            phase=BattlePhase.select_starters,
            current_turn=0,
            players={
                player1_id: PlayerBattleData(
                    player_id=player1_id,
                    spirits=[create_battle_spirit(t, player1_id) for t in p1_templates],
                ),
                player2_id: PlayerBattleData(
                    player_id=player2_id,
                    spirits=[create_battle_spirit(t, player2_id) for t in p2_templates],
                ),
            },
            battle_log=[],
        )
        self._pending: Dict[str, Dict[str, Any]] = {}

    # --- BattleContext ---
    def get_opponent_id(self, player_id: str) -> str:
        return next(pid for pid in self._player_ids if pid != player_id)

    def find_spirit(self, player_id: str, unique_id: str) -> Optional[BattleSpirit]:
        pd = self.state.players.get(player_id)
        if not pd:
            return None
        return next((s for s in pd.spirits if s.unique_id == unique_id), None)

    def find_spirit_anywhere(self, unique_id: str) -> Optional[BattleSpirit]:
        for pid in self._player_ids:
            s = self.find_spirit(pid, unique_id)
            if s:
                return s
        return None

    def get_field_spirits(self, player_id: str) -> List[BattleSpirit]:
        pd = self.state.players.get(player_id)
        if not pd:
            return []
        return [s for s in pd.spirits if s.is_on_field and s.is_alive]

    def get_all_spirits(self, player_id: str) -> List[BattleSpirit]:
        pd = self.state.players.get(player_id)
        return pd.spirits if pd else []

    def add_log(
        self,
        log_type: BattleLogType,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.state.battle_log.append(
            BattleLogEntry(type=log_type, turn=self.state.current_turn, message=message, data=data)
        )

    def execute_normal_attack(
        self,
        player_id: str,
        action: Dict[str, Any],
        is_auto_triggered: bool = False,
    ) -> None:
        self._execute_normal_attack_impl(player_id, action, is_auto_triggered)

    def trigger_starweaver_passive(self, player_id: str, target: BattleSpirit) -> None:
        self._trigger_starweaver_passive_impl(player_id, target)

    # --- starters ---
    def select_starters(self, player_id: str, starter_unique_ids: List[str]) -> bool:
        pd = self.state.players.get(player_id)
        if not pd:
            return False
        if not (1 <= len(starter_unique_ids) <= 4):
            return False
        for uid in starter_unique_ids:
            sp = next((s for s in pd.spirits if s.unique_id == uid), None)
            if not sp:
                return False
            sp.is_on_field = True
        pd.has_submitted_action = True

        if all(self.state.players[pid].has_submitted_action for pid in self._player_ids):
            self.state.phase = BattlePhase.waiting_for_actions
            self.state.current_turn = 1
            for pid in self._player_ids:
                self.state.players[pid].has_submitted_action = False
            self.add_log(BattleLogType.turn_start, "战斗开始！第1回合！")
        return True

    # --- submit ---
    def submit_action(self, player_id: str, action: Dict[str, Any]) -> bool:
        if self.state.phase != BattlePhase.waiting_for_actions:
            return False
        pd = self.state.players.get(player_id)
        if not pd or pd.has_submitted_action:
            return False
        if not self._validate_action(player_id, action):
            return False
        self._pending[player_id] = action
        pd.has_submitted_action = True

        if all(self.state.players[pid].has_submitted_action for pid in self._player_ids):
            self._execute_turn()
        return True

    def _validate_action(self, player_id: str, action: Dict[str, Any]) -> bool:
        pd = self.state.players[player_id]
        at = action.get("type")
        if at == ActionType.normal_attack.value or at == ActionType.use_skill.value:
            aid = action.get("actorId")
            if not aid:
                return False
            actor = self.find_spirit(player_id, aid)
            if not actor or not actor.is_on_field or not actor.is_alive:
                return False
            if is_stunned(actor):
                return False
            if at == ActionType.use_skill.value:
                sk = action.get("skillId")
                if not sk:
                    return False
                tpl = get_spirit_template(actor.template_id)
                if not tpl or not any(s.id == sk for s in tpl.skills):
                    return False
                if actor.template_id == "starweaver":
                    skill = next(s for s in tpl.skills if s.id == sk)
                    ec = skill.energy_cost
                    if ec is not None and ec > 0 and (actor.energy or 0) < ec:
                        return False
                    if ec == -1 and (actor.energy or 0) <= 0:
                        return False
                else:
                    if (actor.skill_cooldowns.get(sk) or 0) > 0:
                        return False
            if action.get("targetId"):
                if not self.find_spirit_anywhere(action["targetId"]):
                    return False
            return True

        if at == ActionType.deploy.value:
            did = action.get("deployId")
            if not did:
                return False
            spirit = self.find_spirit(player_id, did)
            if not spirit or not spirit.is_alive or spirit.is_on_field:
                return False
            on_field = sum(1 for s in pd.spirits if s.is_on_field and s.is_alive)
            return on_field < 4

        if at == ActionType.withdraw.value:
            wid = action.get("withdrawId")
            if not wid:
                return False
            spirit = self.find_spirit(player_id, wid)
            return bool(spirit and spirit.is_on_field and spirit.is_alive)

        if at == ActionType.swap.value:
            w = action.get("withdrawId")
            d = action.get("deployId")
            if not w or not d:
                return False
            ws = self.find_spirit(player_id, w)
            ds = self.find_spirit(player_id, d)
            if not ws or not ws.is_on_field or not ws.is_alive:
                return False
            if not ds or not ds.is_alive or ds.is_on_field:
                return False
            return True

        if at == ActionType.skip.value:
            return True
        return False

    def _execute_turn(self) -> None:
        self.state.phase = BattlePhase.processing
        try:
            ordered = self._sort_actions_by_speed()
            for player_id, action in ordered:
                if self._check_battle_end():
                    break
                self._execute_action(player_id, action)
            self._end_of_turn_processing()
        except Exception as exc:  # noqa: BLE001
            print("回合执行出错:", exc)
            self.add_log(BattleLogType.turn_start, "回合执行时发生了异常，已跳过。")

        if not self._check_battle_end():
            self.state.current_turn += 1
            self.state.phase = BattlePhase.waiting_for_actions
            for pid in self._player_ids:
                self.state.players[pid].has_submitted_action = False
            self._pending.clear()
            self.add_log(BattleLogType.turn_start, f"第{self.state.current_turn}回合！")

    def _sort_actions_by_speed(self) -> List[Tuple[str, Dict[str, Any]]]:
        result: List[Tuple[str, Dict[str, Any], int]] = []
        for player_id, action in self._pending.items():
            speed = 0
            at = action.get("type")
            if at in (ActionType.normal_attack.value, ActionType.use_skill.value):
                actor = self.find_spirit(player_id, action.get("actorId") or "")
                if actor:
                    speed = get_effective_speed(actor)
            elif at == ActionType.deploy.value:
                sp = self.find_spirit(player_id, action.get("deployId") or "")
                if sp:
                    speed = get_effective_speed(sp)
            elif at == ActionType.withdraw.value:
                sp = self.find_spirit(player_id, action.get("withdrawId") or "")
                if sp:
                    speed = get_effective_speed(sp)
            elif at == ActionType.swap.value:
                sp = self.find_spirit(player_id, action.get("withdrawId") or "")
                if sp:
                    speed = get_effective_speed(sp)
            elif at == ActionType.skip.value:
                speed = 0
            result.append((player_id, action, speed))
        result.sort(key=lambda x: x[2], reverse=True)
        return [(a[0], a[1]) for a in result]

    def _execute_action(self, player_id: str, action: Dict[str, Any]) -> None:
        at = action.get("type")
        opponent_id = self.get_opponent_id(player_id)
        if at == ActionType.normal_attack.value:
            self._execute_normal_attack_impl(player_id, action, False)
        elif at == ActionType.use_skill.value:
            self._execute_skill(player_id, action)
        elif at == ActionType.deploy.value:
            self._execute_deploy(player_id, action)
        elif at == ActionType.withdraw.value:
            self._execute_withdraw(player_id, action)
        elif at == ActionType.swap.value:
            self._execute_swap(player_id, action)
        elif at == ActionType.skip.value:
            self.add_log(BattleLogType.action_executed, "玩家选择了跳过本回合。")

        self._check_all_passives(player_id)
        self._check_all_passives(opponent_id)

    def _execute_normal_attack_impl(
        self,
        player_id: str,
        action: Dict[str, Any],
        is_auto_triggered: bool,
    ) -> None:
        actor = self.find_spirit(player_id, action.get("actorId") or "")
        if not actor or not actor.is_alive or not actor.is_on_field:
            return
        if is_stunned(actor) and not is_auto_triggered:
            return

        opponent_id = self.get_opponent_id(player_id)
        targets: List[BattleSpirit] = []

        has_aoe = (
            not is_auto_triggered
            and any(
                e.type == EffectType.attack_enhance and e.enhance_type == "aoe"
                for e in actor.effects
            )
        )
        if has_aoe:
            targets = list(self.get_field_spirits(opponent_id))
        elif action.get("targetId"):
            t = self.find_spirit_anywhere(action["targetId"])
            if t and t.is_alive and t.is_on_field:
                targets = [t]

        if not targets:
            ef = self.get_field_spirits(opponent_id)
            if ef:
                targets = ef if has_aoe else [random.choice(ef)]

        if not targets:
            return

        atk = get_effective_stat(actor, StatType.atk)
        has_stun_enh = (
            not is_auto_triggered
            and any(
                e.type == EffectType.attack_enhance and e.enhance_type == "stun"
                for e in actor.effects
            )
        )
        magic_enh = next(
            (
                e
                for e in actor.effects
                if e.type == EffectType.attack_enhance and e.enhance_type == "magic_damage"
            ),
            None,
        )

        for target in targets:
            raw_phys = atk * 1.0
            phys = calculate_damage(raw_phys, DamageType.physical, actor, target)
            actual_phys = apply_damage(target, phys)
            consume_next_damage_reduction(target)
            self.add_log(
                BattleLogType.damage_dealt,
                f"{actor.name} 对 {target.name} 造成了 {actual_phys} 点物理伤害！",
                {"attackerId": actor.unique_id, "targetId": target.unique_id, "damage": actual_phys},
            )

            if magic_enh and magic_enh.magic_damage_ratio:
                mag_atk = get_effective_stat(actor, StatType.mag_atk)
                raw_mag = mag_atk * magic_enh.magic_damage_ratio
                mag = calculate_damage(raw_mag, DamageType.magical, actor, target)
                actual_mag = apply_damage(target, mag)
                consume_next_damage_reduction(target)
                self.add_log(
                    BattleLogType.damage_dealt,
                    f"{actor.name} 的利爪强化对 {target.name} 额外造成了 {actual_mag} 点魔法伤害！",
                    {"attackerId": actor.unique_id, "targetId": target.unique_id, "damage": actual_mag},
                )

            if has_stun_enh and target.is_alive and not is_debuff_immune(target):
                target.effects.append(
                    make_effect(
                        EffectType.stun,
                        actor.unique_id,
                        remaining_turns=2,
                        is_debuff=True,
                    )
                )
                self.add_log(
                    BattleLogType.effect_applied,
                    f"{target.name} 被眩晕了2回合！",
                    {"targetId": target.unique_id},
                )

            self._trigger_starweaver_passive_impl(player_id, target)
            if not target.is_alive:
                self.add_log(BattleLogType.spirit_defeated, f"{target.name} 被击败了！", {"targetId": target.unique_id})

        if not is_auto_triggered:
            actor.effects = [
                e
                for e in actor.effects
                if not (
                    e.type == EffectType.attack_enhance
                    and e.enhance_type in ("stun", "aoe")
                )
            ]

        logic = get_spirit_logic(actor.template_id)
        if logic and logic.on_after_normal_attack:
            logic.on_after_normal_attack(self, player_id, actor, is_auto_triggered)

    def _execute_skill(self, player_id: str, action: Dict[str, Any]) -> None:
        actor = self.find_spirit(player_id, action.get("actorId") or "")
        if not actor or not actor.is_alive or not actor.is_on_field:
            return
        if is_stunned(actor):
            return
        tpl = get_spirit_template(actor.template_id)
        if not tpl:
            return
        sk = action.get("skillId")
        skill = next((s for s in tpl.skills if s.id == sk), None)
        if not skill:
            return

        self.add_log(
            BattleLogType.action_executed,
            f"{actor.name} 使用了 {skill.name}！",
            {"actorId": actor.unique_id, "skillId": skill.id},
        )

        if actor.template_id != "starweaver" and skill.cooldown > 0:
            actor.skill_cooldowns[skill.id] = skill.cooldown

        if actor.template_id == "starweaver" and skill.energy_cost is not None:
            if skill.energy_cost == -1:
                consumed = actor.energy or 0
                setattr(actor, "_starweaver_consumed_energy", consumed)
                actor.energy = 0
            elif skill.energy_cost > 0:
                actor.energy = (actor.energy or 0) - skill.energy_cost

        logic = get_spirit_logic(actor.template_id)
        if logic:
            logic.execute_skill(self, player_id, actor, action)
            if logic.on_after_skill and actor.is_alive and actor.is_on_field:
                logic.on_after_skill(self, player_id, actor)

    def _execute_deploy(self, player_id: str, action: Dict[str, Any]) -> None:
        spirit = self.find_spirit(player_id, action.get("deployId") or "")
        if not spirit or not spirit.is_alive or spirit.is_on_field:
            return
        spirit.is_on_field = True
        self.add_log(BattleLogType.spirit_deployed, f"{spirit.name} 上场了！", {"spiritId": spirit.unique_id})

    def _execute_withdraw(self, player_id: str, action: Dict[str, Any]) -> None:
        spirit = self.find_spirit(player_id, action.get("withdrawId") or "")
        if not spirit or not spirit.is_on_field or not spirit.is_alive:
            return
        spirit.is_on_field = False
        spirit.effects = [
            e
            for e in spirit.effects
            if not (
                e.type == EffectType.attack_enhance
                and e.enhance_type in ("stun", "aoe")
            )
        ]
        spirit.effects = [e for e in spirit.effects if e.type != EffectType.channeling_skill]
        self.add_log(BattleLogType.spirit_withdrawn, f"{spirit.name} 下场了！", {"spiritId": spirit.unique_id})

    def _execute_swap(self, player_id: str, action: Dict[str, Any]) -> None:
        w = self.find_spirit(player_id, action.get("withdrawId") or "")
        d = self.find_spirit(player_id, action.get("deployId") or "")
        if not w or not d:
            return
        if not w.is_on_field or not w.is_alive:
            return
        if not d.is_alive or d.is_on_field:
            return
        w.is_on_field = False
        d.is_on_field = True
        w.effects = [
            e
            for e in w.effects
            if not (
                e.type == EffectType.attack_enhance
                and e.enhance_type in ("stun", "aoe")
            )
        ]
        w.effects = [e for e in w.effects if e.type != EffectType.channeling_skill]
        self.add_log(
            BattleLogType.spirit_swapped,
            f"{w.name} 下场，{d.name} 上场！",
            {"withdrawId": w.unique_id, "deployId": d.unique_id},
        )

    def _check_all_passives(self, player_id: str) -> None:
        pd = self.state.players.get(player_id)
        if not pd:
            return
        tids = {s.template_id for s in pd.spirits}
        for tid in tids:
            logic = get_spirit_logic(tid)
            if logic and logic.check_passive:
                logic.check_passive(self, player_id)

    def _trigger_starweaver_passive_impl(self, player_id: str, target: BattleSpirit) -> None:
        if not target.is_alive:
            return
        pd = self.state.players.get(player_id)
        if not pd:
            return
        star = next(
            (
                s
                for s in pd.spirits
                if s.template_id == "starweaver" and s.is_alive and (s.energy or 0) > 0
            ),
            None,
        )
        if not star:
            return
        star.energy = (star.energy or 0) - 1
        fixed = apply_damage(target, 40)
        self.add_log(
            BattleLogType.passive_triggered,
            f"{star.name} 的星能共振触发！对 {target.name} 造成了 {fixed} 点固伤！（剩余能量：{star.energy}）",
            {"starweaverId": star.unique_id, "targetId": target.unique_id},
        )
        if not target.is_alive:
            self.add_log(BattleLogType.spirit_defeated, f"{target.name} 被击败了！", {"targetId": target.unique_id})

    def _end_of_turn_processing(self) -> None:
        for pid in self._player_ids:
            pd = self.state.players[pid]
            for spirit in pd.spirits:
                if not spirit.is_alive:
                    continue
                logic = get_spirit_logic(spirit.template_id)
                if logic and logic.on_end_of_turn:
                    logic.on_end_of_turn(self, spirit)
                for eff in tick_effects(spirit):
                    self.add_log(
                        BattleLogType.effect_removed,
                        f"{spirit.name} 的一个效果到期消失了。",
                        {"targetId": spirit.unique_id, "effectId": eff.id},
                    )
                for skid in list(spirit.skill_cooldowns.keys()):
                    if spirit.skill_cooldowns[skid] > 0:
                        spirit.skill_cooldowns[skid] -= 1

    def _check_battle_end(self) -> bool:
        for pid in self._player_ids:
            pd = self.state.players[pid]
            if all(not s.is_alive for s in pd.spirits):
                winner = self.get_opponent_id(pid)
                self.state.phase = BattlePhase.finished
                self.state.winner_id = winner
                self.add_log(BattleLogType.battle_end, f"战斗结束！玩家 {winner} 获胜！", {"winnerId": winner})
                return True
        return False

    def get_visible_state(self, player_id: str) -> BattleState:
        st = copy.deepcopy(self.state)
        oid = self.get_opponent_id(player_id)
        od = st.players.get(oid)
        if od:
            new_spirits: List[BattleSpirit] = []
            for s in od.spirits:
                if not s.is_on_field and s.is_alive:
                    s.effects = []
                    s.skill_cooldowns = {}
                new_spirits.append(s)
            od.spirits = new_spirits
        return st
