"""Reusable tkinter windows for the desktop client."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict, List, Optional

from roco.core.battle.engine import MIN_TEAM_SIZE
from roco.core.battle.types import BattleSpirit
from roco.core.spirits import ALL_SPIRITS

from .constants import DEFAULT_P1, DEFAULT_P2, UI_FONT
from .helpers import center_on_parent
from .theme import Colors, apply_theme, configure_listbox


def _style_popup(window: tk.Toplevel) -> None:
    apply_theme(window)


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
    _TEAM_COLS = 4
    _SELECT_BORDER = "#2563eb"
    _TILE_AVATAR = 64

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
        self._image_refs: List[tk.PhotoImage] = []
        self._p1_tiles: Dict[int, tk.Frame] = {}
        self._p2_tiles: Dict[int, tk.Frame] = {}
        self._p1_badges: Dict[int, tk.Label] = {}
        self._p2_badges: Dict[int, tk.Label] = {}

        wrap = ttk.Frame(self, padding=12)
        wrap.pack(fill=tk.BOTH, expand=True)
        hint = (
            f"每边至少 {MIN_TEAM_SIZE} 只，人数可不限、可不同，可重复选同宠；"
            "左键添加、右键减少（点击顺序即上场顺序）"
        )
        ttk.Label(wrap, text=hint).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Label(wrap, text="我方 (Player 1)", style="Section.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 12)
        )
        ttk.Label(wrap, text="对手 (Player 2)", style="Section.TLabel").grid(
            row=1, column=1, sticky="w"
        )

        p1_grid = ttk.Frame(wrap)
        p1_grid.grid(row=2, column=0, sticky="nw", padx=(0, 12))
        p2_grid = ttk.Frame(wrap)
        p2_grid.grid(row=2, column=1, sticky="nw")

        for idx, tpl in enumerate(ALL_SPIRITS):
            row, col = divmod(idx, self._TEAM_COLS)
            self._build_spirit_tile(p1_grid, idx, tpl, row, col, side=1)
            self._build_spirit_tile(p2_grid, idx, tpl, row, col, side=2)

        btn_row = ttk.Frame(wrap)
        btn_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
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

    def _load_tile_avatar(self, tpl) -> Optional[tk.PhotoImage]:
        loader = getattr(self.master, "_load_avatar", None)
        if not callable(loader):
            return None
        img = loader(
            tpl.name,
            template_id=tpl.id,
            max_size=self._TILE_AVATAR,
        )
        if img is not None:
            self._image_refs.append(img)
        return img

    def _build_spirit_tile(
        self,
        parent: ttk.Frame,
        idx: int,
        tpl,
        row: int,
        col: int,
        *,
        side: int,
    ) -> None:
        cell = tk.Frame(
            parent,
            padx=2,
            pady=2,
            relief=tk.FLAT,
            borderwidth=1,
            bg=Colors.PANEL,
            highlightbackground=Colors.BORDER,
            highlightthickness=1,
        )
        cell.grid(row=row, column=col, padx=4, pady=4)
        tiles = self._p1_tiles if side == 1 else self._p2_tiles
        badges = self._p1_badges if side == 1 else self._p2_badges
        tiles[idx] = cell

        img = self._load_tile_avatar(tpl)
        if img:
            img_lbl = tk.Label(
                cell, image=img, cursor="hand2", bg=Colors.PANEL, borderwidth=0
            )
            img_lbl.image = img
        else:
            img_lbl = tk.Label(
                cell,
                text="无图",
                width=8,
                height=4,
                cursor="hand2",
                bg=Colors.PANEL,
                fg=Colors.TEXT_MUTED,
                borderwidth=0,
            )
        img_lbl.pack()
        name_lbl = tk.Label(
            cell,
            text=tpl.name,
            font=UI_FONT,
            cursor="hand2",
            bg=Colors.PANEL,
            fg=Colors.TEXT,
            borderwidth=0,
        )
        name_lbl.pack(pady=(2, 0))

        badge = tk.Label(
            cell,
            text="",
            font=("Microsoft YaHei UI", 11, "bold"),
            fg="white",
            bg=self._SELECT_BORDER,
            padx=5,
            pady=1,
        )
        badge.place(x=4, y=4, anchor="nw")
        badge.place_forget()
        badges[idx] = badge

        for widget in (cell, img_lbl, name_lbl, badge):
            widget.bind(
                "<Button-1>",
                lambda _e, i=idx, s=side: self._add_spirit(i, s),
            )
            widget.bind(
                "<Button-3>",
                lambda _e, i=idx, s=side: self._remove_spirit(i, s),
            )

    def _add_spirit(self, idx: int, side: int) -> None:
        ordered = self._p1_selected_order if side == 1 else self._p2_selected_order
        ordered.append(idx)
        self._refresh_side_ui(side)

    def _remove_spirit(self, idx: int, side: int) -> None:
        ordered = self._p1_selected_order if side == 1 else self._p2_selected_order
        for i in range(len(ordered) - 1, -1, -1):
            if ordered[i] == idx:
                ordered.pop(i)
                self._refresh_side_ui(side)
                return

    def _refresh_side_ui(self, side: int) -> None:
        if side == 1:
            ordered = self._p1_selected_order
            badges = self._p1_badges
            tiles = self._p1_tiles
        else:
            ordered = self._p2_selected_order
            badges = self._p2_badges
            tiles = self._p2_tiles
        counts: Dict[int, int] = {}
        for spirit_idx in ordered:
            counts[spirit_idx] = counts.get(spirit_idx, 0) + 1
        for idx, badge in badges.items():
            count = counts.get(idx, 0)
            if count:
                badge.configure(text=str(count) if count == 1 else f"×{count}")
                badge.place(x=4, y=4, anchor="nw")
                badge.lift()
            else:
                badge.configure(text="")
                badge.place_forget()
        for idx, cell in tiles.items():
            if counts.get(idx, 0):
                cell.configure(
                    highlightthickness=2,
                    highlightbackground=self._SELECT_BORDER,
                    highlightcolor=self._SELECT_BORDER,
                )
            else:
                cell.configure(
                    highlightthickness=1,
                    highlightbackground=Colors.BORDER,
                    highlightcolor=Colors.BORDER,
                )

    def _ids_from_selection(self, side: int) -> List[str]:
        ordered = self._p1_selected_order if side == 1 else self._p2_selected_order
        return [ALL_SPIRITS[i].id for i in ordered]

    def _use_default(self) -> None:
        self.destroy()
        self._on_confirm(DEFAULT_P1[:], DEFAULT_P2[:])

    def _submit(self) -> None:
        p1_ids = self._ids_from_selection(1)
        p2_ids = self._ids_from_selection(2)
        if len(p1_ids) < MIN_TEAM_SIZE:
            messagebox.showwarning("选择无效", f"Player 1 至少需要 {MIN_TEAM_SIZE} 只精灵。")
            return
        if len(p2_ids) < MIN_TEAM_SIZE:
            messagebox.showwarning("选择无效", f"Player 2 至少需要 {MIN_TEAM_SIZE} 只精灵。")
            return
        self.destroy()
        self._on_confirm(p1_ids, p2_ids)

