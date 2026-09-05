"""Reusable tkinter windows for the desktop client."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, List

from roco.core.battle.engine import MAX_TEAM_SIZE, MIN_TEAM_SIZE
from roco.core.battle.types import BattleSpirit
from roco.core.spirits import ALL_SPIRITS

from .constants import DEFAULT_P1, DEFAULT_P2, UI_FONT
from .helpers import center_on_parent
from .theme import (
    apply_theme,
    configure_listbox,
    configure_log_widget,
    configure_status_widget,
)


def _style_popup(window: tk.Toplevel) -> None:
    apply_theme(window)


class SpiritDetailWindow(tk.Toplevel):
    """Non-modal spirit detail panel; hide on close so the Text widget is reused."""

    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master)
        self.title("精灵详情")
        self.geometry("340x620")
        self.minsize(300, 420)
        _style_popup(self)
        wrap = ttk.Frame(self, padding=10)
        wrap.pack(fill=tk.BOTH, expand=True)
        ttk.Label(wrap, text="精灵详情", style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        self.status_text = tk.Text(wrap, wrap="word", state="disabled")
        configure_status_widget(self.status_text)
        self.status_text.pack(fill=tk.BOTH, expand=True)
        self.protocol("WM_DELETE_WINDOW", self.hide)
        self.withdraw()

    def show(self) -> None:
        if not self.winfo_ismapped():
            self.deiconify()
            self.update_idletasks()
        self.dock()
        self.lift()

    def dock(self) -> None:
        """Attach to the left of the main window with aligned top edges."""
        master = self.master
        width = 340
        height = max(420, master.winfo_height())
        x = max(0, master.winfo_x() - width)
        y = max(0, master.winfo_y())
        self.geometry(f"{width}x{height}{x:+d}{y:+d}")

    def hide(self) -> None:
        self.withdraw()


class BattleLogWindow(tk.Toplevel):
    """Non-modal battle log; hide on close so incremental append keeps working."""

    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master)
        self.title("战斗日志")
        self.geometry("340x640")
        self.minsize(300, 360)
        _style_popup(self)
        wrap = ttk.Frame(self, padding=10)
        wrap.pack(fill=tk.BOTH, expand=True)
        ttk.Label(wrap, text="战斗记录", style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        self.log_text = tk.Text(wrap, wrap="word", state="disabled")
        configure_log_widget(self.log_text)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.protocol("WM_DELETE_WINDOW", self.hide)
        self.withdraw()

    def show(self) -> None:
        if not self.winfo_ismapped():
            self.deiconify()
            self.update_idletasks()
        self.dock()
        self.lift()

    def dock(self) -> None:
        """Attach to the right of the main window with aligned top edges."""
        master = self.master
        width = 340
        height = max(360, master.winfo_height())
        x = min(
            master.winfo_screenwidth() - width,
            master.winfo_x() + master.winfo_width(),
        )
        y = max(0, master.winfo_y())
        self.geometry(f"{width}x{height}{x:+d}{y:+d}")

    def hide(self) -> None:
        self.withdraw()

class TargetWindow(tk.Toplevel):
    def __init__(
        self,
        master: tk.Tk,
        title: str,
        targets: List[BattleSpirit],
        key_fn: Callable[[BattleSpirit, int], str],
        submit: Callable[[BattleSpirit], None],
        *,
        cancellable: bool = True,
    ) -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        _style_popup(self)
        wrap = ttk.Frame(self, padding=10)
        wrap.pack(fill=tk.BOTH, expand=True)
        ttk.Label(wrap, text="选择目标", style="Section.TLabel").pack(anchor="w")
        p1_id = getattr(master, "p1", "p1")
        for i, t in enumerate(targets, 1):
            player = "player1" if t.owner_id == p1_id else "player2"
            text = f"[{key_fn(t, i)}] {t.name} {player}"
            ttk.Button(wrap, text=text, command=lambda s=t: self._choose(submit, s)).pack(
                fill=tk.X, pady=2
            )
        if cancellable:
            ttk.Button(wrap, text="取消", command=self.destroy).pack(fill=tk.X, pady=(8, 0))
            self.protocol("WM_DELETE_WINDOW", self.destroy)
        else:
            self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.update_idletasks()
        center_on_parent(self, master)

    def _choose(self, submit: Callable[[BattleSpirit], None], spirit: BattleSpirit) -> None:
        self.destroy()
        submit(spirit)


class IndexChoiceWindow(tk.Toplevel):
    """Pick one item by index from a labeled list."""

    def __init__(
        self,
        master: tk.Tk,
        title: str,
        prompt: str,
        labels: List[str],
        submit: Callable[[int], None],
    ) -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        _style_popup(self)
        wrap = ttk.Frame(self, padding=10)
        wrap.pack(fill=tk.BOTH, expand=True)
        ttk.Label(wrap, text=prompt, font=UI_FONT).pack(anchor="w", pady=(0, 8))
        for i, text in enumerate(labels):
            ttk.Button(
                wrap,
                text=text,
                command=lambda idx=i: self._choose(submit, idx),
            ).pack(fill=tk.X, pady=2)
        ttk.Button(wrap, text="取消", command=self.destroy).pack(fill=tk.X, pady=(8, 0))
        self.update_idletasks()
        center_on_parent(self, master)

    def _choose(self, submit: Callable[[int], None], index: int) -> None:
        self.destroy()
        submit(index)


class MultiPickWindow(tk.Toplevel):
    """Pick one or more hand slots (multi-select)."""

    def __init__(
        self,
        master: tk.Tk,
        title: str,
        prompt: str,
        labels: List[str],
        submit: Callable[[List[int]], None],
        *,
        min_pick: int = 1,
    ) -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        _style_popup(self)
        self._min_pick = min_pick
        self._submit = submit
        wrap = ttk.Frame(self, padding=10)
        wrap.pack(fill=tk.BOTH, expand=True)
        ttk.Label(wrap, text=prompt, font=UI_FONT).pack(anchor="w", pady=(0, 8))
        self.lb = tk.Listbox(
            wrap, selectmode=tk.MULTIPLE, exportselection=False, height=min(10, max(4, len(labels)))
        )
        configure_listbox(self.lb)
        for text in labels:
            self.lb.insert(tk.END, text)
        self.lb.pack(fill=tk.BOTH, expand=True)
        ttk.Button(wrap, text="确认", command=self._confirm).pack(fill=tk.X, pady=(8, 0))
        ttk.Button(wrap, text="取消", command=self.destroy).pack(fill=tk.X, pady=(4, 0))
        self.update_idletasks()
        center_on_parent(self, master)

    def _confirm(self) -> None:
        picked = list(self.lb.curselection())
        if len(picked) < self._min_pick:
            messagebox.showwarning(
                "选择无效",
                f"请至少选择 {self._min_pick} 张牌（当前 {len(picked)} 张）。",
            )
            return
        self.destroy()
        self._submit(sorted(picked))


class TeamSelectWindow(tk.Toplevel):
    def __init__(
        self,
        master: tk.Tk,
        on_confirm: Callable[[List[str], List[str]], None],
    ) -> None:
        super().__init__(master)
        self.title("选择精灵阵容")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        _style_popup(self)
        self._on_confirm = on_confirm
        self._p1_selected_order: List[int] = []
        self._p2_selected_order: List[int] = []
        self._p1_selected_set: set[int] = set()
        self._p2_selected_set: set[int] = set()

        wrap = ttk.Frame(self, padding=10)
        wrap.pack(fill=tk.BOTH, expand=True)
        hint = f"两边各选 {MIN_TEAM_SIZE}~{MAX_TEAM_SIZE} 只，且数量相同"
        ttk.Label(wrap, text=hint).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self.lb1 = tk.Listbox(wrap, selectmode=tk.MULTIPLE, exportselection=False, height=10, width=24)
        self.lb2 = tk.Listbox(wrap, selectmode=tk.MULTIPLE, exportselection=False, height=10, width=24)
        configure_listbox(self.lb1)
        configure_listbox(self.lb2)
        self.lb1.grid(row=1, column=0, padx=(0, 8))
        self.lb2.grid(row=1, column=1)
        self.lb1.bind("<<ListboxSelect>>", lambda _e: self._sync_selection_order(self.lb1, 1))
        self.lb2.bind("<<ListboxSelect>>", lambda _e: self._sync_selection_order(self.lb2, 2))

        ttk.Label(wrap, text="我方 (Player 1)").grid(row=2, column=0, sticky="w", pady=(4, 0))
        ttk.Label(wrap, text="对手 (Player 2)").grid(row=2, column=1, sticky="w", pady=(4, 0))

        for tpl in ALL_SPIRITS:
            self.lb1.insert(tk.END, tpl.name)
            self.lb2.insert(tk.END, tpl.name)

        btn_row = ttk.Frame(wrap)
        btn_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(btn_row, text="使用默认阵容", command=self._use_default).pack(side=tk.LEFT)
        ttk.Button(
            btn_row,
            text="开始对战",
            style="Primary.TButton",
            command=self._submit,
        ).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_row, text="取消", command=self.destroy).pack(side=tk.LEFT)
        self.update_idletasks()
        center_on_parent(self, master)

    def _sync_selection_order(self, lb: tk.Listbox, side: int) -> None:
        current = set(lb.curselection())
        if side == 1:
            old = self._p1_selected_set
            ordered = self._p1_selected_order
        else:
            old = self._p2_selected_set
            ordered = self._p2_selected_order
        removed = old - current
        added = [i for i in lb.curselection() if i not in old]
        if removed:
            ordered[:] = [i for i in ordered if i not in removed]
        for i in added:
            ordered.append(i)
        if side == 1:
            self._p1_selected_set = current
        else:
            self._p2_selected_set = current

    def _ids_from_selection(self, side: int) -> List[str]:
        ordered = self._p1_selected_order if side == 1 else self._p2_selected_order
        return [ALL_SPIRITS[i].id for i in ordered]

    def _use_default(self) -> None:
        self.destroy()
        self._on_confirm(DEFAULT_P1[:], DEFAULT_P2[:])

    def _submit(self) -> None:
        p1_ids = self._ids_from_selection(1)
        p2_ids = self._ids_from_selection(2)
        if not (MIN_TEAM_SIZE <= len(p1_ids) <= MAX_TEAM_SIZE):
            messagebox.showwarning("选择无效", f"Player 1 需要选择 {MIN_TEAM_SIZE}~{MAX_TEAM_SIZE} 只精灵。")
            return
        if not (MIN_TEAM_SIZE <= len(p2_ids) <= MAX_TEAM_SIZE):
            messagebox.showwarning("选择无效", f"Player 2 需要选择 {MIN_TEAM_SIZE}~{MAX_TEAM_SIZE} 只精灵。")
            return
        if len(p1_ids) != len(p2_ids):
            messagebox.showwarning("选择无效", "两边精灵数量需相同。")
            return
        self.destroy()
        self._on_confirm(p1_ids, p2_ids)

