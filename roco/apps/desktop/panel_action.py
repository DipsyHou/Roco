"""Action bar: buttons for the current actor and action submission."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict, Optional, Set

from roco.core.battle.extra_action import (
    DEFAULT_EXTRA_ACTION_UI,
    ExtraActionUI,
    policy_ui,
)
from roco.core.battle.types import (
    ActionType,
    BattlePhase,
    BattleSpirit,
    TargetType,
    requires_target_pick,
)
from roco.core.spirits import get_spirit_logic, get_spirit_template

from .helpers import _skill_available, _skill_cost_label, pick_targets
from .skill_flows import get_skill_flow


class ActionBarMixin:
    """Renders available actions and routes each choice to the engine."""

    def _clear_action_row(self) -> None:
        for child in self.action_row.winfo_children():
            child.destroy()

    def _armed_action_key(self) -> Optional[str]:
        pick = getattr(self, "_target_pick", None)
        if not pick:
            return None
        source = pick.get("source")
        return str(source) if source else None

    def _apply_extra_action_hint(self, actor: BattleSpirit, slot) -> ExtraActionUI:
        """Return panel rules for ``actor`` (hint text is unused in the UI)."""
        return DEFAULT_EXTRA_ACTION_UI if slot is None else policy_ui(slot.policy_id)

    def _render_skill_buttons(self, eng, actor: BattleSpirit, ui: ExtraActionUI) -> None:
        """Render the actor's skill buttons (shared by local and online panels)."""
        armed = self._armed_action_key()
        tpl = get_spirit_template(actor.template_id)
        for sk in tpl.skills if tpl else []:
            if ui.allowed_skill_ids is not None:
                if sk.id not in ui.allowed_skill_ids:
                    continue
            elif bool(sk.special) != ui.special_skills:
                # 特殊技能只在声明了 special_skills 的额外行动里出现，反之亦然。
                continue
            ok, reason = _skill_available(eng, actor, sk)
            txt = f"{sk.name}({_skill_cost_label(actor, sk, eng)})"
            if not ok:
                txt += f" - {reason}"
            style = "Primary.TButton" if armed == sk.id else "TButton"
            ttk.Button(
                self.action_row,
                text=txt,
                style=style,
                command=lambda skill=sk: self._action_skill(skill),
                state=("normal" if ok else "disabled"),
            ).pack(side=tk.LEFT, padx=2)

    def _render_actions(self) -> None:
        self._clear_action_row()
        eng = self.eng
        assert eng
        if eng.state.phase == BattlePhase.finished:
            return
        actor = eng.find_spirit_anywhere(eng.state.active_actor_id or "")
        if not actor or not actor.is_alive:
            return
        blocked = self._turn_block_reason(actor)
        if blocked is not None:
            ttk.Label(self.action_row, text=blocked, style="Muted.TLabel").pack(
                side=tk.LEFT
            )
            return
        if eng.state.active_turn_stunned:
            ttk.Label(
                self.action_row,
                text=f"{actor.name} 眩晕中，自动跳过",
                style="Muted.TLabel",
            ).pack(side=tk.LEFT, padx=(0, 8))
            ttk.Button(
                self.action_row, text="执行跳过", command=self._submit_stun_skip
            ).pack(side=tk.LEFT)
            return
        slot = eng.current_extra_slot() if hasattr(eng, "current_extra_slot") else None
        ui = self._apply_extra_action_hint(actor, slot)
        armed = self._armed_action_key()
        if ui.allow_normal_attack:
            ttk.Button(
                self.action_row,
                text="普攻",
                style=("Primary.TButton" if armed == "normal" else "TButton"),
                command=self._action_normal,
            ).pack(side=tk.LEFT, padx=3)
        if ui.allow_skip:
            ttk.Button(
                self.action_row, text="跳过", command=self._action_skip
            ).pack(side=tk.LEFT, padx=2)
        if ui.allow_gather:
            ttk.Button(self.action_row, text="聚能", command=self._action_gather).pack(
                side=tk.LEFT, padx=2
            )
        self._render_skill_buttons(eng, actor, ui)

    def _clear_target_pick(self, *, restore_actions: bool = True) -> None:
        if getattr(self, "_target_pick", None) is None:
            return
        self._target_pick = None
        try:
            self.unbind("<Escape>")
        except tk.TclError:
            pass
        stop = getattr(self, "_stop_target_pulse", None)
        if callable(stop):
            stop()
        update = getattr(self, "_update_pet_selection_highlights", None)
        if callable(update):
            update()
        if restore_actions and self.eng and self.eng.state.phase != BattlePhase.finished:
            self._render_actions()

    def _cancel_target_pick(self) -> None:
        pick = getattr(self, "_target_pick", None)
        if not pick or not pick.get("cancellable", True):
            return
        self._clear_target_pick(restore_actions=True)

    def _on_target_pick_escape(self, _event=None) -> Optional[str]:
        pick = getattr(self, "_target_pick", None)
        if pick and pick.get("cancellable", True):
            self._cancel_target_pick()
            return "break"
        return None

    def _submit_action(self, action: Dict[str, object]) -> None:
        eng = self.eng
        assert eng
        if getattr(self, "_fx_busy", False):
            return
        # Committing an action always leaves target-pick mode.
        self._clear_target_pick(restore_actions=False)
        actor = eng.find_spirit_anywhere(eng.state.active_actor_id or "")
        if not actor:
            return
        if self._turn_block_reason(actor) is not None:
            messagebox.showinfo("提示", "还没轮到你行动。")
            return
        log_start = self._rendered_log_count
        highlight_id = eng.state.active_actor_id
        try:
            ok = eng.submit_action(actor.owner_id, action)
        except RuntimeError as exc:
            # Remote engine raises when the socket dropped mid-battle.
            messagebox.showwarning("联机", str(exc))
            return
        if not ok:
            messagebox.showwarning("无效行动", "行动未通过校验，请重试。")
            return
        self._fx_pending_log_start = log_start
        self._fx_pending_highlight_id = highlight_id
        self._after_submit()

    def _submit_stun_skip(self) -> None:
        eng = self.eng
        assert eng
        actor = eng.find_spirit_anywhere(eng.state.active_actor_id or "")
        if not actor:
            return
        self._submit_action(
            {"type": ActionType.skip.value, "playerId": actor.owner_id, "actorId": actor.unique_id}
        )

    def _action_skip(self) -> None:
        self._submit_stun_skip()

    def _probe_action_allowed(
        self, actor: BattleSpirit, action: Dict[str, object]
    ) -> bool:
        """Whether ``action`` would pass engine / spirit hard checks."""
        eng = self.eng
        if eng is None:
            return False
        validate = getattr(eng, "_validate_action", None)
        if callable(validate):
            return bool(validate(actor.owner_id, action, actor))
        # RemoteBattleEngine has no local validator; honor spirit constraints.
        logic = get_spirit_logic(actor.template_id)
        if logic is None:
            return True
        slot = eng.current_extra_slot() if hasattr(eng, "current_extra_slot") else None
        custom = logic.can_execute_action(
            eng,
            actor,
            action,
            in_extra_action=slot is not None,
            stunned=bool(getattr(eng.state, "active_turn_stunned", False)),
        )
        if custom is not None:
            return bool(custom[0])
        return True

    def _filter_pick_targets(
        self,
        actor: BattleSpirit,
        targets: list,
        probe_action: Optional[Callable[[BattleSpirit], Dict[str, object]]],
    ) -> list:
        """Drop candidates the engine would reject (e.g. 呱呱不能选自己)."""
        if not probe_action or not targets:
            return targets
        return [
            t for t in targets if self._probe_action_allowed(actor, probe_action(t))
        ]

    def _pick_target(
        self,
        mode: str,
        callback: Callable[[BattleSpirit], None],
        *,
        cancellable: bool = True,
        source: str = "",
        probe_action: Optional[Callable[[BattleSpirit], Dict[str, object]]] = None,
        targets_override: Optional[list] = None,
    ) -> None:
        """Arm an action and highlight valid battlefield targets."""
        eng = self.eng
        assert eng
        if getattr(self, "_fx_busy", False):
            return
        actor = eng.find_spirit_anywhere(eng.state.active_actor_id or "")
        if not actor:
            return
        raw = (
            list(targets_override)
            if targets_override is not None
            else pick_targets(eng, actor, mode)
        )
        targets = self._filter_pick_targets(actor, raw, probe_action)
        if not targets:
            messagebox.showinfo("提示", "当前没有可选目标。")
            return
        ids: Set[str] = {t.unique_id for t in targets}
        self._target_pick = {
            "mode": mode,
            "callback": callback,
            "cancellable": cancellable,
            "ids": ids,
            "actor_id": actor.unique_id,
            "source": source,
        }
        self.bind("<Escape>", self._on_target_pick_escape)
        start = getattr(self, "_start_target_pulse", None)
        if callable(start):
            start()
        else:
            update = getattr(self, "_update_pet_selection_highlights", None)
            if callable(update):
                update()
        self._render_actions()

    def _action_gather(self) -> None:
        eng = self.eng
        assert eng
        actor = eng.find_spirit_anywhere(eng.state.active_actor_id or "")
        if not actor:
            return
        self._submit_action(
            {
                "type": ActionType.gather_energy.value,
                "playerId": actor.owner_id,
                "actorId": actor.unique_id,
            }
        )

    def _action_normal(self) -> None:
        eng = self.eng
        assert eng
        actor = eng.find_spirit_anywhere(eng.state.active_actor_id or "")
        if not actor:
            return
        if self._armed_action_key() == "normal":
            self._cancel_target_pick()
            return

        def _go(target: BattleSpirit) -> None:
            self._submit_action(
                {
                    "type": ActionType.normal_attack.value,
                    "playerId": actor.owner_id,
                    "actorId": actor.unique_id,
                    "targetId": target.unique_id,
                }
            )

        def _probe(target: BattleSpirit) -> Dict[str, object]:
            return {
                "type": ActionType.normal_attack.value,
                "playerId": actor.owner_id,
                "actorId": actor.unique_id,
                "targetId": target.unique_id,
            }

        self._pick_target("enemy", _go, source="normal", probe_action=_probe)

    def _action_skill(self, sk) -> None:
        eng = self.eng
        assert eng
        actor = eng.find_spirit_anywhere(eng.state.active_actor_id or "")
        if not actor:
            return
        if self._armed_action_key() == sk.id:
            self._cancel_target_pick()
            return
        flow = get_skill_flow(sk.id)
        if flow is not None:
            # Custom flows may still open dialogs; leave target-pick first.
            self._clear_target_pick(restore_actions=False)
            flow(self, actor)
            return
        base = {
            "type": ActionType.use_skill.value,
            "playerId": actor.owner_id,
            "actorId": actor.unique_id,
            "skillId": sk.id,
        }

        def _probe(target: BattleSpirit) -> Dict[str, object]:
            # Confirm-only skills omit targetId; single-target skills include it.
            return {**base, "targetId": target.unique_id}

        tt = sk.target_type
        logic = get_spirit_logic(actor.template_id)
        if logic:
            override = logic.get_skill_target_type(eng, actor, sk)
            if override is not None:
                tt = override
        if not requires_target_pick(tt):
            # Self / AoE: arm first, pulse affected spirits, click to confirm.
            # ``none``: no pick — pulse implied launch targets if any, else fire now.
            if tt == TargetType.self:
                mode = "self"
            elif tt == TargetType.all_enemies:
                mode = "enemy"
            elif tt == TargetType.all_allies:
                mode = "ally"
            elif tt == TargetType.none:
                implied: list = []
                if logic:
                    raw = logic.get_attack_launch_targets(eng, actor, base, sk)
                    if raw:
                        implied = [t for t in raw if t is not None and t.is_alive]
                if not implied:
                    self._submit_action(base)
                    return

                def _probe_none(_target: BattleSpirit) -> Dict[str, object]:
                    return dict(base)

                self._pick_target(
                    "any",
                    lambda _t: self._submit_action(base),
                    source=sk.id,
                    probe_action=_probe_none,
                    targets_override=implied,
                )
                return
            else:
                self._submit_action(base)
                return

            def _probe_confirm(_target: BattleSpirit) -> Dict[str, object]:
                return dict(base)

            self._pick_target(
                mode,
                lambda _t: self._submit_action(base),
                source=sk.id,
                probe_action=_probe_confirm,
            )
            return
        if tt == TargetType.single_enemy:
            mode = "enemy"
        elif tt in (TargetType.single_ally, TargetType.single_ally_on_field):
            mode = "ally"
        else:
            mode = "any"
        self._pick_target(
            mode,
            lambda t: self._submit_action({**base, "targetId": t.unique_id}),
            source=sk.id,
            probe_action=_probe,
        )
