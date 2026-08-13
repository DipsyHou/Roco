"""Timeline battle engine — 5v5 action-value scheduler."""

from __future__ import annotations

import copy
import logging
import secrets
import uuid
from typing import Any, Dict, List, Optional

from .types import (
    ActionType,
    BattleLogEntry,
    BattleLogType,
    BattlePhase,
    BattleSpirit,
    BattleState,
    PlayerBattleData,
    SpiritTemplate,
)
from .rules import (
    MAX_TEAM_SIZE,
    MIN_TEAM_SIZE,
)
from .events import DamageEvent, DamageSource, dispatch_damage
from .extra_action import ExtraActionSlot, policy_allows
from .energy import EnergyManager
from .action_executor import ActionExecutor
from .formation import living_slot_neighbors
from .timeline_controller import TimelineController
from .rng import RandomSource
from .snapshot import restore_snapshot, take_snapshot
from . import messages as msg
from .turn_pipeline import TurnPipeline
from ..spirits import get_spirit_logic, get_spirit_template
from .timeline import ACTION_GAP
from .stats import bind_spirit_stat_engine

logger = logging.getLogger(__name__)


def create_battle_spirit(
    template: SpiritTemplate,
    owner_id: str,
    slot: int,
) -> BattleSpirit:
    bs = template.base_stats
    spirit = BattleSpirit(
        unique_id=str(uuid.uuid4()),
        template_id=template.id,
        owner_id=owner_id,
        name=template.name,
        base_stats=copy.deepcopy(bs),
        current_hp=bs.hp,
        max_hp=bs.hp,
        slot=slot,
        charge=float(ACTION_GAP),
        effects=[],
        skill_cooldowns={},
        is_alive=True,
    )
    logic = get_spirit_logic(template.id)
    if logic:
        logic.on_unit_created(spirit)
    return spirit


class BattleEngine:
    def __init__(
        self,
        battle_id: str,
        player1_id: str,
        player2_id: str,
        p1_templates: List[SpiritTemplate],
        p2_templates: List[SpiritTemplate],
    ) -> None:
        for label, team in [("Player 1", p1_templates), ("Player 2", p2_templates)]:
            n = len(team)
            if n < MIN_TEAM_SIZE or n > MAX_TEAM_SIZE:
                raise ValueError(
                    f"{label} needs {MIN_TEAM_SIZE}~{MAX_TEAM_SIZE} spirits, got {n}"
                )

        self._player_ids = [player1_id, player2_id]
        self.state = BattleState(
            battle_id=battle_id,
            phase=BattlePhase.waiting_for_action,
            action_count=0,
            rng_seed=secrets.token_hex(8),
            players={
                player1_id: PlayerBattleData(
                    player_id=player1_id,
                    spirits=[
                        create_battle_spirit(t, player1_id, i + 1)
                        for i, t in enumerate(p1_templates)
                    ],
                ),
                player2_id: PlayerBattleData(
                    player_id=player2_id,
                    spirits=[
                        create_battle_spirit(t, player2_id, i + 1)
                        for i, t in enumerate(p2_templates)
                    ],
                ),
            },
            battle_log=[],
        )
        self._pipeline = TurnPipeline(self)
        self._energy = EnergyManager(self)
        self._actions = ActionExecutor(self)
        self._timeline = TimelineController(self)
        self._rng = RandomSource(self.state.rng_seed, self.state.rng_counters)
        self._suspended_turn_actor_id: Optional[str] = None
        self._suspended_turn_action: Optional[Dict[str, Any]] = None
        self._suspended_turn_stunned: bool = False

        for pid in self._player_ids:
            for spirit in self.state.players[pid].spirits:
                bind_spirit_stat_engine(spirit, self)
                logic = get_spirit_logic(spirit.template_id)
                if logic:
                    logic.on_battle_start(self, spirit)

        self.add_log(BattleLogType.turn_start, msg.BATTLE_START)
        self._set_active_actor()
        self._refresh_timeline_preview()

    # --- BattleContext ---
    @property
    def battle_id(self) -> str:
        return self.state.battle_id

    @property
    def player_ids(self) -> List[str]:
        """Public, ordered [player1_id, player2_id]."""
        return list(self._player_ids)

    def next_rng(self, domain: str, *parts: Any):
        """Deterministic per-domain RNG for one random draw (see rng.py)."""
        return self._rng.next(domain, *parts)

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

    def get_active_spirits(self, player_id: str) -> List[BattleSpirit]:
        pd = self.state.players.get(player_id)
        if not pd:
            return []
        return [s for s in pd.spirits if s.is_alive]

    def get_all_spirits(self, player_id: str) -> List[BattleSpirit]:
        pd = self.state.players.get(player_id)
        return pd.spirits if pd else []

    def get_adjacent_enemies(self, target: BattleSpirit) -> List[BattleSpirit]:
        """同阵营按槽位排序后的左右邻（仅存活；中间阵亡不挡扩散）。"""
        return living_slot_neighbors(self.get_active_spirits(target.owner_id), target)

    def get_adjacent_allies(
        self, anchor: BattleSpirit, player_id: str
    ) -> List[BattleSpirit]:
        """锚点精灵及其左右邻己方场上精灵（仅存活；中间阵亡不挡）。"""
        return [anchor] + living_slot_neighbors(
            self.get_active_spirits(player_id), anchor
        )

    def add_log(
        self,
        log_type: BattleLogType,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.state.battle_log.append(
            BattleLogEntry(
                type=log_type,
                turn=self.state.action_count,
                message=message,
                data=data,
            )
        )

    def execute_normal_attack(
        self,
        player_id: str,
        action: Dict[str, Any],
        is_auto_triggered: bool = False,
    ) -> None:
        self._actions.execute_normal_attack_impl(player_id, action, is_auto_triggered)

    def notify_damage_taken(
        self,
        attacker: Optional[BattleSpirit],
        target: BattleSpirit,
        damage: int,
        *,
        source: DamageSource = DamageSource.other,
    ) -> None:
        dispatch_damage(
            self,
            DamageEvent(
                attacker=attacker,
                target=target,
                damage=damage,
                source=source,
            ),
        )

    # --- timeline ---
    def _all_alive_spirits(self) -> List[BattleSpirit]:
        return self._timeline.all_alive_spirits()

    def after_actor_acts(self, actor: BattleSpirit) -> None:
        logic = get_spirit_logic(actor.template_id)
        if logic and actor.is_alive:
            logic.on_after_actor_acts(self, actor)

    def get_effective_speed(self, spirit: BattleSpirit) -> float:
        return self._timeline.get_effective_speed(spirit)

    def advance_action(self, target: BattleSpirit, percent: float) -> None:
        self._timeline.advance_action(target, percent)

    def delay_action(self, target: BattleSpirit, percent: float) -> None:
        self._timeline.delay_action(target, percent)

    def _set_active_actor(self) -> None:
        self.state.active_actor_id = self._timeline.pick_next_actor_id()
        self.state.turn_prepared_actor_id = None
        self.state.active_turn_stunned = False

    def advance_past_dead_active(self) -> None:
        """Active actor died before acting (e.g. DoT at turn start); pick next alive.

        Public so the online server's turn-sync loop doesn't reach into engine
        internals; the local turn pipeline uses it as well.
        """
        if self.state.phase == BattlePhase.finished:
            return
        self.state.turn_prepared_actor_id = None
        self.state.active_turn_stunned = False
        self._set_active_actor()
        self._refresh_timeline_preview()
        if self._check_battle_end():
            return
        self._begin_turn_if_needed()

    # Back-compat internal alias (pre-existing call sites).
    _advance_past_dead_active = advance_past_dead_active

    def ensure_active_turn_begun(self) -> None:
        """轮到行动者时先结算行动开始系统处理，再等待玩家输入。"""
        self._begin_turn_if_needed()

    def _begin_turn_if_needed(self) -> None:
        actor_id = self.state.active_actor_id
        if not actor_id or actor_id == self.state.turn_prepared_actor_id:
            return
        actor = self.find_spirit_anywhere(actor_id)
        if not actor:
            return
        if not actor.is_alive:
            self._advance_past_dead_active()
            return
        self._timeline.advance_time_to_actor(actor)
        self.state.active_turn_stunned = self._pipeline.begin_turn(actor)
        self.state.turn_prepared_actor_id = actor_id
        if not actor.is_alive:
            self._advance_past_dead_active()

    def _refresh_timeline_preview(self) -> None:
        self._timeline.refresh_preview()

    # --- extra-action queue (unified) ---
    def current_extra_slot(self) -> Optional[ExtraActionSlot]:
        q = self.state.extra_action_queue
        return q[0] if q else None

    def queue_extra_actions(
        self,
        slots: List[ExtraActionSlot],
        *,
        front: bool = False,
    ) -> None:
        """Append (default) or insert-at-front a list of extra-action slots.

        - ``front=False``：追加到队尾（共舞排队加入多个队友）。
        - ``front=True``：插队到最前（同一精灵连锁；插入顺序保留）。

        死亡 / 不存在的目标自动跳过。
        """
        valid: List[ExtraActionSlot] = []
        for slot in slots:
            spirit = self.find_spirit_anywhere(slot.actor_id)
            if spirit and spirit.is_alive:
                valid.append(slot)
        if not valid:
            return
        if front:
            self.state.extra_action_queue = list(valid) + self.state.extra_action_queue
        else:
            self.state.extra_action_queue = self.state.extra_action_queue + list(valid)

    def _prune_extra_action_queue(self) -> None:
        kept: List[ExtraActionSlot] = []
        for slot in self.state.extra_action_queue:
            spirit = self.find_spirit_anywhere(slot.actor_id)
            if spirit and spirit.is_alive:
                kept.append(slot)
        self.state.extra_action_queue = kept

    def _activate_extra_slot(self, slot: ExtraActionSlot) -> bool:
        actor = self.find_spirit_anywhere(slot.actor_id)
        if not actor or not actor.is_alive:
            return False
        self.state.active_actor_id = actor.unique_id
        self.state.turn_prepared_actor_id = actor.unique_id
        self.state.active_turn_stunned = False
        return True

    def _advance_to_next_extra_slot(self) -> bool:
        """Pop dead slots; activate next live one. Returns True if any activated."""
        self._prune_extra_action_queue()
        while self.state.extra_action_queue:
            if self._activate_extra_slot(self.state.extra_action_queue[0]):
                return True
            self.state.extra_action_queue.pop(0)
        return False

    # --- submit ---
    def submit_action(self, player_id: str, action: Dict[str, Any]) -> bool:
        if self.state.phase != BattlePhase.waiting_for_action:
            return False
        actor_id = self.state.active_actor_id
        if not actor_id:
            return False
        actor = self.find_spirit_anywhere(actor_id)
        if not actor or actor.owner_id != player_id:
            return False

        # 藤椒出锅：先掷菜写进 sync_attrs，不推进回合；UI 再按菜选目标。
        if action.get("previewDish"):
            return self._preview_tengjiao_dish(player_id, actor, action)

        slot = self.current_extra_slot()
        if slot:
            if not self._validate_action(player_id, action, actor):
                return False
            snapshot = take_snapshot(self)
            self.state.phase = BattlePhase.processing
            try:
                self._pipeline.resolve_inserted_extra_action(actor, action)
            except Exception:  # noqa: BLE001
                self._abort_action(snapshot, actor, action)
                return False
            if self._check_battle_end():
                return True
            # execute may have queued more extras at front (chain) or back.
            # Pop the slot we just resolved (it's at position 0 unless logic inserted
            # in front; pop the matching slot if so).
            self._pop_resolved_slot(slot)
            if self._advance_to_next_extra_slot():
                self._refresh_timeline_preview()
                self.state.phase = BattlePhase.waiting_for_action
                return True
            return self._finish_suspended_turn_if_any()

        self.ensure_active_turn_begun()
        if not self._validate_action(player_id, action, actor):
            return False

        snapshot = take_snapshot(self)
        self.state.phase = BattlePhase.processing
        try:
            self._process_action_turn(actor, action)
        except Exception:  # noqa: BLE001
            self._abort_action(snapshot, actor, action)
            return False

        if self._check_battle_end():
            return True

        stunned = self.state.active_turn_stunned
        # During execute, logic may have queued extras (self-chain via front=True,
        # or external-insert via append). Suspend the normal turn until queue drains.
        if self._advance_to_next_extra_slot():
            self._suspended_turn_actor_id = actor.unique_id
            self._suspended_turn_action = dict(action)
            self._suspended_turn_stunned = stunned
            self._refresh_timeline_preview()
            self.state.phase = BattlePhase.waiting_for_action
            return True

        return self._finish_normal_turn(player_id, actor, action, stunned)

    def _preview_tengjiao_dish(
        self,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> bool:
        """Roll/commit 出锅 dish into sync_attrs without spending the turn."""
        if action.get("type") != ActionType.use_skill.value:
            return False
        if action.get("skillId") != "tengjiao_skill3":
            return False
        if actor.template_id != "tengjiao":
            return False
        if not self._validate_action(player_id, action, actor):
            return False
        from roco.core.spirits.tengjiao import tengjiao_logic

        tengjiao_logic.prepare_serve_dish(self, actor)
        return True

    def _abort_action(
        self,
        snapshot,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        """Roll back a half-executed action and log the failure.

        Spirit logic raised partway through, so energy may already be spent and
        damage partly applied. We restore the pre-action state, then re-append a
        single log line so players see that the action failed — the partial
        entries written before the exception are discarded with the state.
        """
        discarded = restore_snapshot(self, snapshot)
        logger.exception(
            "action failed: battle=%s actor=%s (%s) action=%s; rolled back, "
            "discarded %d log entr%s",
            self.state.battle_id,
            actor.unique_id,
            actor.template_id,
            action.get("skillId") or action.get("type"),
            len(discarded),
            "y" if len(discarded) == 1 else "ies",
        )
        self.add_log(
            BattleLogType.action_executed,
            msg.ACTION_EXCEPTION,
            {"actorId": actor.unique_id},
        )
        self.state.phase = BattlePhase.waiting_for_action

    def _pop_resolved_slot(self, resolved: ExtraActionSlot) -> None:
        """Remove the slot we just resolved. Tolerates queue mutation by logic."""
        q = self.state.extra_action_queue
        for i, s in enumerate(q):
            if s is resolved or (
                s.actor_id == resolved.actor_id and s.policy_id == resolved.policy_id
            ):
                q.pop(i)
                return

    def _finish_normal_turn(
        self,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
        stunned: bool,
    ) -> bool:
        self._pipeline.end_turn(actor, action, player_id=player_id, stunned=stunned)
        if self._check_battle_end():
            return True
        self.state.action_count += 1
        pd = self.state.players.get(player_id)
        if pd:
            pd.team_energy_spent_tracker = 0
        self._set_active_actor()
        self._refresh_timeline_preview()
        self._begin_turn_if_needed()
        self.state.phase = BattlePhase.waiting_for_action
        return True

    def _finish_suspended_turn_if_any(self) -> bool:
        """Called when extra-action queue drained. Resume the suspended normal turn
        (if any) and run its end_turn. Otherwise pick next actor normally."""
        actor_id = self._suspended_turn_actor_id
        action = self._suspended_turn_action
        stunned = self._suspended_turn_stunned
        self._suspended_turn_actor_id = None
        self._suspended_turn_action = None
        self._suspended_turn_stunned = False
        if not actor_id or action is None:
            # 若 turn_prepared 仍未消化（on_turn_start 中插入的额外行动已排空），
            # 回到 waiting_for_action 让当前行动者继续正常回合。
            if self.state.turn_prepared_actor_id:
                self.state.phase = BattlePhase.waiting_for_action
                return True
            self._set_active_actor()
            self._refresh_timeline_preview()
            self._begin_turn_if_needed()
            self.state.phase = BattlePhase.waiting_for_action
            return True
        actor = self.find_spirit_anywhere(actor_id)
        if not actor:
            self._set_active_actor()
            self._refresh_timeline_preview()
            self._begin_turn_if_needed()
            self.state.phase = BattlePhase.waiting_for_action
            return True
        return self._finish_normal_turn(actor.owner_id, actor, action, stunned)

    def _validate_action(
        self,
        player_id: str,
        action: Dict[str, Any],
        actor: BattleSpirit,
    ) -> bool:
        at = action.get("type")
        aid = action.get("actorId")
        if aid != actor.unique_id:
            return False

        # 额外行动期：按当前 slot 的 policy 过滤
        slot = self.current_extra_slot()
        if slot is not None:
            if slot.actor_id != actor.unique_id:
                return False
            if not policy_allows(slot, actor, action):
                return False

        logic = get_spirit_logic(actor.template_id)
        if logic:
            custom = logic.can_execute_action(
                self,
                actor,
                action,
                in_extra_action=slot is not None,
                stunned=self.state.active_turn_stunned,
            )
            if custom is not None and not custom[0]:
                return False

        if at in (ActionType.skip.value, ActionType.gather_energy.value):
            return actor.is_alive

        if at in (ActionType.normal_attack.value, ActionType.use_skill.value):
            if not actor.is_alive:
                return False
            if at == ActionType.use_skill.value:
                sk = action.get("skillId")
                if not sk:
                    return False
                tpl = get_spirit_template(actor.template_id)
                if not tpl or not any(s.id == sk for s in tpl.skills):
                    return False
                skill = next(s for s in tpl.skills if s.id == sk)
                logic = get_spirit_logic(actor.template_id)
                if logic:
                    custom = logic.can_use_skill(actor, skill)
                    if custom is not None:
                        return custom[0]
                if not self._can_pay_team_energy(player_id, actor, skill):
                    return False
            tid = action.get("targetId")
            if tid:
                target = self.find_spirit_anywhere(tid)
                if not target or not target.is_alive:
                    return False
            return True

        return False

    def _can_pay_team_energy(self, player_id: str, actor: BattleSpirit, skill) -> bool:
        return self._energy.can_pay(player_id, actor, skill)

    def _team_energy_cost(self, actor: BattleSpirit, skill) -> int:
        return self._energy.cost(actor, skill)

    def effective_skill_energy_cost(self, actor: BattleSpirit, skill) -> int:
        """Public helper for UIs: team-energy cost after spirit-specific modifiers."""
        return self._energy.cost(actor, skill)

    def gain_team_energy(
        self,
        player_id: str,
        amount: int,
        *,
        reason: Optional[str] = None,
        log_type: Any = None,
        silent: bool = False,
    ) -> int:
        return self._energy.gain(
            player_id, amount, reason=reason, log_type=log_type, silent=silent
        )

    # Back-compat internal alias.
    _gain_team_energy = gain_team_energy

    def sync_team_energy_cap(self, player_id: str) -> int:
        return self._energy.sync_cap(player_id)

    def get_team_energy_spent(self, player_id: str) -> int:
        return self._energy.get_spent(player_id)

    def reset_team_energy_spent(self, player_id: str) -> None:
        self._energy.reset_spent(player_id)

    def _spend_team_energy(self, player_id: str, actor: BattleSpirit, skill) -> None:
        self._energy.spend(player_id, actor, skill)

    def _process_action_turn(
        self, actor: BattleSpirit, action: Dict[str, Any]
    ) -> None:
        self._pipeline.resolve_turn(
            actor,
            action,
            stunned=self.state.active_turn_stunned,
            defer_end_turn=True,
        )

    def log_effect_expired(self, spirit: BattleSpirit, eff) -> None:
        self.add_log(
            BattleLogType.effect_removed,
            msg.effect_expired(spirit.name),
            {"targetId": spirit.unique_id, "effectId": eff.id},
        )

    def execute_action(self, player_id: str, action: Dict[str, Any]) -> None:
        self._actions.execute_action(player_id, action)

    def notify_spirit_defeated(self, defeated: BattleSpirit) -> None:
        for pid in self._player_ids:
            for spirit in self.state.players[pid].spirits:
                spirit_logic = get_spirit_logic(spirit.template_id)
                if spirit_logic:
                    spirit_logic.on_spirit_defeated(self, spirit, defeated)

    def _check_battle_end(self) -> bool:
        for pid in self._player_ids:
            pd = self.state.players[pid]
            if all(not s.is_alive for s in pd.spirits):
                winner = self.get_opponent_id(pid)
                self.state.phase = BattlePhase.finished
                self.state.winner_id = winner
                self.state.active_actor_id = None
                self.add_log(
                    BattleLogType.battle_end,
                    msg.battle_end(winner),
                    {"winnerId": winner},
                )
                return True
        return False
