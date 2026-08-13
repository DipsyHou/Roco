"""Action bar: buttons for the current actor and action submission."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict

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
from .windows import TargetWindow


class ActionBarMixin:
    """Renders available actions and routes each choice to the engine."""

    def _clear_action_row(self) -> None:
        for child in self.action_row.winfo_children():
            child.destroy()

    def _apply_extra_action_hint(self, actor: BattleSpirit, slot) -> ExtraActionUI:
        """Set ``action_hint`` for ``actor`` and return the panel rules to use.

        Presentation rules live with each extra-action policy (see
        ``register_policy``), so adding a spirit does not touch this method.
        """
        ui = DEFAULT_EXTRA_ACTION_UI if slot is None else policy_ui(slot.policy_id)
        self.action_hint.set(f"{actor.name} 可行动{ui.hint}：")
        return ui

    def _render_skill_buttons(self, eng, actor: BattleSpirit, ui: ExtraActionUI) -> None:
        """Render the actor's skill buttons (shared by local and online panels)."""
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
            ttk.Button(
                self.action_row,
                text=txt,
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
            self.action_hint.set(blocked)
            return
        if eng.state.active_turn_stunned:
            self.action_hint.set(f"{actor.name} 眩晕中，自动跳过")
            ttk.Button(
                self.action_row, text="执行跳过", command=self._submit_stun_skip
            ).pack(side=tk.LEFT)
            return
        slot = eng.current_extra_slot() if hasattr(eng, "current_extra_slot") else None
        ui = self._apply_extra_action_hint(actor, slot)
        if ui.allow_normal_attack:
            ttk.Button(
                self.action_row,
                text="普攻",
                style="Primary.TButton",
                command=self._action_normal,
            ).pack(side=tk.LEFT, padx=3)
        if ui.allow_skip:
            ttk.Button(
                self.action_row, text="跳过", command=self._submit_stun_skip
            ).pack(side=tk.LEFT, padx=2)
        if ui.allow_gather:
            ttk.Button(self.action_row, text="聚能", command=self._action_gather).pack(
                side=tk.LEFT, padx=2
            )
        self._render_skill_buttons(eng, actor, ui)

    def _submit_action(self, action: Dict[str, object]) -> None:
        eng = self.eng
        assert eng
        actor = eng.find_spirit_anywhere(eng.state.active_actor_id or "")
        if not actor:
            return
        if self._turn_block_reason(actor) is not None:
            messagebox.showinfo("提示", "还没轮到你行动。")
            return
        try:
            ok = eng.submit_action(actor.owner_id, action)
        except RuntimeError as exc:
            # Remote engine raises when the socket dropped mid-battle.
            messagebox.showwarning("联机", str(exc))
            return
        if not ok:
            messagebox.showwarning("无效行动", "行动未通过校验，请重试。")
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

    def _pick_target(
        self,
        mode: str,
        callback: Callable[[BattleSpirit], None],
        *,
        cancellable: bool = True,
    ) -> None:
        eng = self.eng
        assert eng
        actor = eng.find_spirit_anywhere(eng.state.active_actor_id or "")
        if not actor:
            return
        targets = pick_targets(eng, actor, mode)
        if mode in ("enemy", "ally"):
            key_fn = lambda s, i: str(s.slot)
        else:
            key_fn = lambda s, i: str(i)
        if not targets:
            messagebox.showinfo("提示", "当前没有可选目标。")
            return
        TargetWindow(
            self, "选择目标", targets, key_fn, callback, cancellable=cancellable
        )

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

        def _go(target: BattleSpirit) -> None:
            self._submit_action(
                {
                    "type": ActionType.normal_attack.value,
                    "playerId": actor.owner_id,
                    "actorId": actor.unique_id,
                    "targetId": target.unique_id,
                }
            )

        self._pick_target("enemy", _go)

    def _action_skill(self, sk) -> None:
        eng = self.eng
        assert eng
        actor = eng.find_spirit_anywhere(eng.state.active_actor_id or "")
        if not actor:
            return
        flow = get_skill_flow(sk.id)
        if flow is not None:
            flow(self, actor)
            return
        base = {
            "type": ActionType.use_skill.value,
            "playerId": actor.owner_id,
            "actorId": actor.unique_id,
            "skillId": sk.id,
        }
        tt = sk.target_type
        logic = get_spirit_logic(actor.template_id)
        if logic:
            override = logic.get_skill_target_type(eng, actor, sk)
            if override is not None:
                tt = override
        if not requires_target_pick(tt):
            self._submit_action(base)
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
        )
