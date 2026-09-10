"""Main tkinter desktop application."""

from __future__ import annotations

import tkinter as tk
import uuid
from tkinter import messagebox, ttk
from typing import Dict, List, Optional

from roco.core.ai import choose_action
from roco.core.battle.engine import BattleEngine, MIN_TEAM_SIZE
from roco.core.battle.rules import MAX_DEAD_ACTOR_SKIPS
from roco.core.battle.types import ActionType, BattlePhase, BattleSpirit

from .combat_fx import CombatFxMixin
from .constants import DEFAULT_P1, DEFAULT_P2, SIDE_PANEL_WIDTH, WINDOW_HEIGHT, WINDOW_WIDTH
from .helpers import _runtime_root, _templates_from_ids
from .panel_action import ActionBarMixin
from .panel_avatar import AvatarMixin
from .panel_log import LogPanelMixin
from .panel_petstrip import PetStripMixin
from .panel_status import StatusPanelMixin
from .panel_timeline import TimelineMixin
from .theme import Colors, apply_theme, configure_log_widget, configure_status_widget
from .windows import TeamSelectWindow


class DesktopGameApp(
    AvatarMixin,
    PetStripMixin,
    TimelineMixin,
    StatusPanelMixin,
    LogPanelMixin,
    ActionBarMixin,
    CombatFxMixin,
    tk.Tk,
):
    """Local battle window.

    Panel rendering lives in the ``panel_*`` mixins; this class owns the window,
    the engine lifecycle, and the refresh loop. The five ``_engine_is_*`` /
    ``_header_text`` style hooks below are the seams the online app overrides.
    """

    def __init__(self) -> None:
        super().__init__()
        # Force Tcl/Tk to use UTF-8; cp936 can render some CJK as \uXXXX escapes.
        self.tk.call("encoding", "system", "utf-8")
        self.title("Roco")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(1280, 720)
        self.eng: Optional[BattleEngine] = None
        self.p1 = "p1"
        self.p2 = "p2"
        self.ai_host_p1 = False
        self.ai_host_p2 = False
        self._host_p1_var = tk.BooleanVar(value=False)
        self._host_p2_var = tk.BooleanVar(value=False)
        self._ai_job: Optional[str] = None
        self.selected_spirit_id: Optional[str] = None
        self._target_pick: Optional[Dict[str, object]] = None
        self._rendered_log_count = 0
        self._init_combat_fx()
        self.asset_dir = _runtime_root() / "assets" / "spirits"
        self.marks_dir = _runtime_root() / "assets" / "marks"
        self.ui_dir = _runtime_root() / "assets" / "ui"
        self._image_cache: Dict[str, tk.PhotoImage] = {}
        self._pil_cache: Dict[str, object] = {}
        self._timeline_image_refs: List[tk.PhotoImage] = []
        self._pet_card_widgets: Dict[str, Dict[str, object]] = {}
        self._team_strip_widgets: Dict[str, Dict[str, object]] = {}
        apply_theme(self)
        icon_path = _runtime_root() / "assets" / "seed.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass
        self._build_ui()
        self.update_idletasks()
        self._center_main_window()
        self._start_default_battle()

    def _center_main_window(self) -> None:
        width = self.winfo_width()
        height = self.winfo_height()
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (self.winfo_screenheight() - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=10)
        top.pack(fill=tk.X)
        self._build_header_buttons(top)
        # Kept as state for local/online refresh policies; intentionally hidden.
        self.header_var = tk.StringVar(value="准备中…")

        mid = ttk.Frame(self, padding=10)
        mid.pack(fill=tk.BOTH, expand=True)

        # ttk.Frame ignores width/propagate; use tk.Frame to pin the side rail.
        right = tk.Frame(mid, width=SIDE_PANEL_WIDTH, bg=Colors.BG)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        right.pack_propagate(False)
        right.grid_propagate(False)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        detail = ttk.Frame(right)
        detail.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        ttk.Label(detail, text="精灵详情", style="Section.TLabel").pack(
            anchor="w", pady=(0, 6)
        )
        self.status_text = self._build_scrollable_text(detail, configure_status_widget)

        log_panel = ttk.Frame(right)
        log_panel.grid(row=1, column=0, sticky="nsew")
        ttk.Label(log_panel, text="战斗记录", style="Section.TLabel").pack(
            anchor="w", pady=(0, 6)
        )
        self.log_text = self._build_scrollable_text(log_panel, configure_log_widget)

        left = ttk.Frame(mid, width=200)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        left.pack_propagate(False)
        ttk.Label(left, text="时间轴", style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        self.timeline_frame = tk.Frame(
            left,
            bg=Colors.BG,
            highlightthickness=0,
        )
        self.timeline_frame.pack(fill=tk.BOTH, expand=True)

        self.pet_strip = ttk.Frame(mid)
        self.pet_strip.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        bottom = ttk.Frame(self, padding=(10, 4, 10, 10))
        bottom.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.action_hint = tk.StringVar(value="")
        self.action_row = ttk.Frame(bottom)
        self.action_row.pack(fill=tk.X)

    def _build_scrollable_text(self, parent: ttk.Frame, configure) -> tk.Text:
        """Text widget with a vertical scrollbar and mouse-wheel scrolling."""
        row = ttk.Frame(parent)
        row.pack(fill=tk.BOTH, expand=True)
        text = tk.Text(row, wrap="word", state="disabled", width=1)
        configure(text)
        scroll = ttk.Scrollbar(row, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_wheel(event) -> str:
            text.yview_scroll(int(-event.delta / 120), "units")
            return "break"

        text.bind("<MouseWheel>", _on_wheel)
        return text

    def _build_header_buttons(self, top: ttk.Frame) -> None:
        ttk.Button(
            top,
            text="开始对局",
            style="Primary.TButton",
            command=self._open_team_selector,
        ).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(top, text="AI托管").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Checkbutton(
            top,
            text="P1",
            variable=self._host_p1_var,
            command=self._on_host_toggle,
        ).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Checkbutton(
            top,
            text="P2",
            variable=self._host_p2_var,
            command=self._on_host_toggle,
        ).pack(side=tk.LEFT)

    def _on_host_toggle(self) -> None:
        """Apply mid-battle AI hosting for P1/P2 and resume the turn loop."""
        self.ai_host_p1 = bool(self._host_p1_var.get())
        self.ai_host_p2 = bool(self._host_p2_var.get())
        self._cancel_ai_job()
        if self.eng and self.eng.state.phase != BattlePhase.finished:
            self._refresh()

    def _sync_host_vars_from_state(self) -> None:
        self._host_p1_var.set(bool(self.ai_host_p1))
        self._host_p2_var.set(bool(self.ai_host_p2))

    def _clear_log_widget(self) -> None:
        self._rendered_log_count = 0
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

    def _start_default_battle(self) -> None:
        self._start_battle(DEFAULT_P1[:], DEFAULT_P2[:])

    def _open_team_selector(self) -> None:
        TeamSelectWindow(self, self._start_battle)

    def _cancel_ai_job(self) -> None:
        if self._ai_job is not None:
            try:
                self.after_cancel(self._ai_job)
            except Exception:
                pass
            self._ai_job = None

    def _start_battle(
        self,
        p1_ids: List[str],
        p2_ids: List[str],
    ) -> None:
        if len(p1_ids) < MIN_TEAM_SIZE:
            messagebox.showerror("错误", f"Player 1 至少需要 {MIN_TEAM_SIZE} 只精灵。")
            return
        if len(p2_ids) < MIN_TEAM_SIZE:
            messagebox.showerror("错误", f"Player 2 至少需要 {MIN_TEAM_SIZE} 只精灵。")
            return
        p1_tpls = _templates_from_ids(p1_ids)
        p2_tpls = _templates_from_ids(p2_ids)
        if len(p1_tpls) < MIN_TEAM_SIZE or len(p2_tpls) < MIN_TEAM_SIZE:
            messagebox.showerror("错误", "默认队伍模板缺失，无法开始。")
            return
        self._cancel_ai_job()
        self._cancel_combat_fx()
        self._clear_target_pick(restore_actions=False)
        # 开局默认双方手动；对局中用顶部「AI托管」切换。
        self.ai_host_p1 = False
        self.ai_host_p2 = False
        self._sync_host_vars_from_state()
        self.eng = BattleEngine(str(uuid.uuid4()), self.p1, self.p2, p1_tpls, p2_tpls)
        if self.eng.state.players[self.p1].spirits:
            self.selected_spirit_id = self.eng.state.players[self.p1].spirits[0].unique_id
        self.title("Roco")
        self._clear_log_widget()
        self._reset_pet_strip()
        self._refresh()

    def _player_is_ai(self, player_id: str) -> bool:
        """Whether ``player_id`` is driven by local AI hosting."""
        if player_id == self.p1:
            return bool(self.ai_host_p1)
        if player_id == self.p2:
            return bool(self.ai_host_p2)
        return False

    def _force_pick_next_actor(self) -> None:
        """Fallback: directly repick next alive actor if submit_action fails."""
        eng = self.eng
        assert eng
        # Local engine exposes the authoritative repick; the remote mirror only
        # asks the server to advance via ensure_active_turn_begun().
        if hasattr(eng, "advance_past_dead_active"):
            eng.advance_past_dead_active()  # type: ignore[attr-defined]
        else:
            eng.ensure_active_turn_begun()

    # --- subclass policy hooks -------------------------------------------
    # The online app drives the same widgets from a server-synced mirror.
    # Rather than branching on the engine type in every render method, the
    # differences are expressed as these five overridables.

    def _engine_is_authoritative(self) -> bool:
        """True when this app owns the engine and may resolve turns itself."""
        return True

    def _ally_player_id(self) -> str:
        """Player rendered as "我方"; online overrides this with its own seat."""
        return self.p1

    def _enemy_player_id(self) -> str:
        return self.p2 if self._ally_player_id() == self.p1 else self.p1

    def _turn_block_reason(self, actor: BattleSpirit) -> Optional[str]:
        """Hint to show instead of action buttons, or ``None`` when we may act."""
        if getattr(self, "_fx_busy", False):
            return "结算中…"
        if self._player_is_ai(actor.owner_id):
            return f"人机操作中（{actor.name}）…"
        return None

    def _header_text(self, actor: Optional[BattleSpirit]) -> str:
        eng = self.eng
        assert eng
        if eng.state.phase == BattlePhase.finished:
            return "战斗结束"
        if actor is None:
            return "等待行动…"
        if self._player_is_ai(actor.owner_id):
            side = "P1" if actor.owner_id == self.p1 else "P2"
            return f"行动 #{eng.state.action_count + 1} | 人机({side}): {actor.name}"
        player_num = 1 if actor.owner_id == self.p1 else 2
        return f"行动 #{eng.state.action_count + 1} | Player {player_num}: {actor.name}"

    def _before_refresh(self) -> None:
        """Hook run at the top of every refresh (online uses it to sync turns)."""

    def _after_submit(self) -> None:
        """Post-submit step; online instead waits for the server's state push."""
        log_start = getattr(self, "_fx_pending_log_start", self._rendered_log_count)
        highlight_id = getattr(self, "_fx_pending_highlight_id", None)
        from .skill_flows import resume_pending_tengjiao_serve

        self._play_action_fx(
            log_start,
            highlight_actor_id=highlight_id,
            on_complete=lambda: resume_pending_tengjiao_serve(self),
        )

    def _schedule_ai_turn(self) -> None:
        """Queue one AI action if the active player is AI-controlled."""
        self._cancel_ai_job()
        if not self.eng:
            return
        if self.eng.state.phase == BattlePhase.finished:
            return
        actor = self._find_active_actor()
        if not actor or not actor.is_alive or not self._player_is_ai(actor.owner_id):
            return

        def _run_ai() -> None:
            self._ai_job = None
            eng = self.eng
            if not eng:
                return
            if eng.state.phase == BattlePhase.finished:
                return
            actor_now = eng.find_spirit_anywhere(eng.state.active_actor_id or "")
            if not actor_now or not self._player_is_ai(actor_now.owner_id):
                return
            pid = actor_now.owner_id
            log_start = self._rendered_log_count
            highlight_id = eng.state.active_actor_id
            try:
                # Stunned turns: UI normally asks for skip; AI picks legal skip/skill.
                if eng.state.active_turn_stunned:
                    action = {
                        "type": ActionType.skip.value,
                        "playerId": pid,
                        "actorId": actor_now.unique_id,
                    }
                else:
                    action = choose_action(eng, pid)
                ok = eng.submit_action(pid, action)
            except Exception as exc:  # noqa: BLE001
                messagebox.showwarning("人机", f"人机行动失败：{exc}")
                return
            if not ok:
                messagebox.showwarning("人机", "人机行动未通过校验。")
                self._refresh()
                return
            self._play_action_fx(log_start, highlight_actor_id=highlight_id)

        self._ai_job = self.after(180, _run_ai)

    def _find_active_actor(self) -> Optional[BattleSpirit]:
        eng = self.eng
        if not eng:
            return None
        return eng.find_spirit_anywhere(eng.state.active_actor_id or "")

    def _normalize_active_actor(self) -> Optional[BattleSpirit]:
        """Ensure active actor is alive; auto-advance dead actors safely."""
        eng = self.eng
        if not eng:
            return None
        if not self._engine_is_authoritative():
            # 回合开始在服务端已结算；勿每次刷新都 sync_turn（会造成明显卡顿）
            return self._find_active_actor()
        eng.ensure_active_turn_begun()
        actor = self._find_active_actor()
        guard = 0
        while (
            eng.state.phase != BattlePhase.finished
            and actor is not None
            and not actor.is_alive
            and guard < MAX_DEAD_ACTOR_SKIPS
        ):
            ok = eng.submit_action(
                actor.owner_id,
                {
                    "type": ActionType.skip.value,
                    "playerId": actor.owner_id,
                    "actorId": actor.unique_id,
                },
            )
            if not ok:
                self._force_pick_next_actor()
            else:
                eng.ensure_active_turn_begun()
            actor = self._find_active_actor()
            guard += 1
        return actor

    def _render_panels(self) -> None:
        """Redraw the read-only panels (everything except the action row)."""
        self._sync_pet_strip()
        self._render_timeline()
        # Keep popup contents fresh even while withdrawn.
        self._render_status_panel()
        self._render_logs()

    def _refresh(self) -> None:
        eng = self.eng
        if not eng:
            return
        self._before_refresh()
        actor = self._normalize_active_actor()
        # Drop stale target-pick if the turn already moved on.
        pick = getattr(self, "_target_pick", None)
        if pick is not None:
            actor_id = pick.get("actor_id")
            if (
                eng.state.phase == BattlePhase.finished
                or not actor
                or actor.unique_id != actor_id
            ):
                self._clear_target_pick(restore_actions=False)
        self._render_panels()

        if eng.state.phase == BattlePhase.finished:
            self._cancel_ai_job()
            self._clear_action_row()
            winner_id = eng.state.winner_id
            if winner_id == self.p1:
                winner = "人机 P1" if self.ai_host_p1 else "Player 1"
            else:
                winner = "人机 P2" if self.ai_host_p2 else "Player 2"
            ttk.Label(
                self.action_row,
                text=f"战斗结束：{winner} 获胜",
                style="Section.TLabel",
            ).pack(side=tk.LEFT)
            self.header_var.set(self._header_text(None))
            return

        if not actor or not actor.is_alive:
            self._clear_action_row()
            ttk.Label(
                self.action_row,
                text="等待下一位可行动宠物…",
                style="Muted.TLabel",
            ).pack(side=tk.LEFT)
            self.header_var.set(self._header_text(None))
            return

        self.header_var.set(self._header_text(actor))
        self._render_actions()
        if self._player_is_ai(actor.owner_id):
            self._schedule_ai_turn()


def main() -> None:
    app = DesktopGameApp()
    app.mainloop()
