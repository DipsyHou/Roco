"""局外装备养成 — 简易 GUI（tkinter）。

运行：
  python scripts/roll_equipment_gui.py
  python scripts/roll_equipment_demo.py --gui
"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Optional

_SCRIPTS = Path(__file__).resolve().parent
_ROOT = _SCRIPTS.parent
for _p in (_ROOT, _SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from roll_equipment_demo import (  # noqa: E402
    ALL_SPIRITS,
    SLOTS,
    GameState,
    create_equipment,
    delete_equipment,
    equip,
    load_state,
    save_state,
    spirit_panel,
    unequip,
    upgrade_equipment,
)


class EquipmentApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.tk.call("encoding", "system", "utf-8")
        self.title("Roco — 局外装备养成")
        self.geometry("1180x780")
        self.minsize(1000, 640)

        self.state = load_state()
        self.spirit_id: str = ALL_SPIRITS[0].id
        self._inv_uid_map: list[str] = []

        self._build_ui()
        self._refresh_all()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=8)
        root.pack(fill=tk.BOTH, expand=True)

        # --- 左：精灵 ---
        left = ttk.LabelFrame(root, text="精灵", padding=6)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        self.spirit_list = tk.Listbox(left, width=22, height=18, exportselection=False)
        self.spirit_list.pack(fill=tk.Y, expand=True)
        for t in ALL_SPIRITS:
            self.spirit_list.insert(tk.END, t.name)
        self.spirit_list.selection_set(0)
        self.spirit_list.bind("<<ListboxSelect>>", self._on_spirit_select)

        # --- 中：面板 + 已装备 ---
        mid = ttk.Frame(root)
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        panel_frame = ttk.LabelFrame(mid, text="属性面板", padding=6)
        panel_frame.pack(fill=tk.BOTH, expand=True)
        self.panel_text = tk.Text(
            panel_frame, wrap=tk.WORD, height=11, state=tk.DISABLED, font=("Consolas", 10)
        )
        self.panel_text.pack(fill=tk.BOTH, expand=True)

        slots_frame = ttk.LabelFrame(mid, text="当前装备", padding=6)
        slots_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.slot_texts: dict[str, tk.Text] = {}
        self.slot_btns: dict[str, ttk.Frame] = {}
        for slot in SLOTS:
            row = ttk.Frame(slots_frame)
            row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=slot, width=5).pack(side=tk.LEFT, anchor=tk.N, pady=2)
            txt = tk.Text(
                row,
                height=5,
                wrap=tk.WORD,
                state=tk.DISABLED,
                font=("Consolas", 9),
                width=48,
                relief=tk.GROOVE,
                borderwidth=1,
            )
            txt.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
            btn_col = ttk.Frame(row)
            btn_col.pack(side=tk.RIGHT, anchor=tk.N)
            ttk.Button(btn_col, text="升级", width=5, command=lambda s=slot: self._do_upgrade_slot(s)).pack(
                fill=tk.X, pady=(0, 2)
            )
            ttk.Button(btn_col, text="卸下", width=6, command=lambda s=slot: self._do_unequip(s)).pack(
                fill=tk.X, pady=(0, 2)
            )
            ttk.Button(btn_col, text="删除", width=6, command=lambda s=slot: self._do_delete_slot(s)).pack(
                fill=tk.X
            )
            self.slot_texts[slot] = txt
            self.slot_btns[slot] = btn_col

        # --- 右：刷装 + 仓库 ---
        right = ttk.Frame(root, width=380)
        right.pack(side=tk.RIGHT, fill=tk.BOTH)
        right.pack_propagate(False)

        farm = ttk.LabelFrame(right, text="刷取装备", padding=6)
        farm.pack(fill=tk.X)
        for slot in SLOTS:
            ttk.Button(farm, text=f"刷 {slot}", command=lambda s=slot: self._do_farm(s)).pack(
                fill=tk.X, pady=2
            )

        inv_frame = ttk.LabelFrame(right, text="仓库", padding=6)
        inv_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        list_wrap = ttk.Frame(inv_frame)
        list_wrap.pack(fill=tk.BOTH, expand=True)
        self.inv_list = tk.Listbox(
            list_wrap, height=10, exportselection=False, font=("Microsoft YaHei UI", 10)
        )
        inv_scroll = ttk.Scrollbar(list_wrap, orient=tk.VERTICAL, command=self.inv_list.yview)
        self.inv_list.configure(yscrollcommand=inv_scroll.set)
        self.inv_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inv_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.inv_list.bind("<<ListboxSelect>>", self._on_inv_select)
        self.inv_list.bind("<Double-Button-1>", lambda _e: self._do_equip_selected())

        ttk.Label(inv_frame, text="选中详情：").pack(anchor=tk.W, pady=(6, 0))
        self.inv_detail = tk.Text(
            inv_frame, height=5, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 10)
        )
        self.inv_detail.pack(fill=tk.X)

        btn_row = ttk.Frame(inv_frame)
        btn_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(btn_row, text="装备给当前精灵", command=self._do_equip_selected).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(btn_row, text="升级", command=self._do_upgrade_selected).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="删除", command=self._do_delete_selected).pack(side=tk.LEFT)

        self.status = ttk.Label(self, text="", anchor=tk.W, padding=(8, 4))
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_text(self, widget: tk.Text, content: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        widget.configure(state=tk.DISABLED)

    def _equipment_detail(self, eq) -> str:
        aff = "\n".join(f"  · {a.fmt()}" for a in eq.affixes)
        up = f"剩余升级：{eq.upgrades_left} 次" if eq.upgrades_left else "已满升级"
        return f"[{eq.uid[:8]}] {eq.slot}·{eq.name}\n{aff}\n{up}"

    def _on_inv_select(self, _event: Optional[object] = None) -> None:
        uid = self._selected_inv_uid()
        if not uid:
            self._set_text(self.inv_detail, "（未选择）")
            return
        self._set_text(self.inv_detail, self._equipment_detail(self.state.equipment[uid]))

    def _set_status(self, msg: str) -> None:
        self.status.configure(text=msg)

    def _set_slot_actions_enabled(self, slot: str, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        for child in self.slot_btns[slot].winfo_children():
            child.configure(state=state)

    def _confirm_delete(self, label: str) -> bool:
        return messagebox.askyesno("确认删除", f"永久删除以下装备？\n\n{label}", icon="warning")

    def _do_delete_uid(self, uid: str) -> None:
        eq = self.state.equipment.get(uid)
        if not eq:
            return
        if not self._confirm_delete(self._equipment_detail(eq)):
            return
        msg = delete_equipment(self.state, uid)
        self._persist()
        self._refresh_all()
        self._set_status(msg)

    def _do_delete_selected(self) -> None:
        uid = self._selected_inv_uid()
        if not uid:
            messagebox.showinfo("提示", "请先在仓库中选择要删除的装备。")
            return
        self._do_delete_uid(uid)

    def _do_delete_slot(self, slot: str) -> None:
        uid = self.state.loadouts[self.spirit_id][slot]
        if not uid:
            return
        self._do_delete_uid(uid)

    def _on_spirit_select(self, _event: Optional[object] = None) -> None:
        sel = self.spirit_list.curselection()
        if not sel:
            return
        self.spirit_id = ALL_SPIRITS[sel[0]].id
        self._refresh_panel()
        self._refresh_slots()

    def _refresh_panel(self) -> None:
        text = spirit_panel(self.spirit_id, self.state)
        self.panel_text.configure(state=tk.NORMAL)
        self.panel_text.delete("1.0", tk.END)
        self.panel_text.insert(tk.END, text)
        self.panel_text.configure(state=tk.DISABLED)

    def _refresh_slots(self) -> None:
        self.state.ensure_spirits()
        slots = self.state.loadouts[self.spirit_id]
        for slot in SLOTS:
            uid = slots[slot]
            if uid:
                eq = self.state.equipment[uid]
                self._set_text(self.slot_texts[slot], self._equipment_detail(eq))
                self._set_slot_actions_enabled(slot, True)
            else:
                self._set_text(self.slot_texts[slot], "（空）")
                self._set_slot_actions_enabled(slot, False)

    def _refresh_inventory(self, keep_uid: Optional[str] = None) -> None:
        if keep_uid is None:
            keep_uid = self._selected_inv_uid()
        inv = self.state.inventory()
        self._inv_uid_map = [eq.uid for eq in inv]
        self.inv_list.delete(0, tk.END)
        for eq in inv:
            self.inv_list.insert(tk.END, f"{eq.uid[:8]}  {eq.slot}·{eq.name}")
        if not inv:
            self._set_text(self.inv_detail, "仓库为空")
            return
        idx = 0
        if keep_uid and keep_uid in self._inv_uid_map:
            idx = self._inv_uid_map.index(keep_uid)
        self.inv_list.selection_clear(0, tk.END)
        self.inv_list.selection_set(idx)
        self.inv_list.see(idx)
        self._on_inv_select()

    def _refresh_all(self, keep_inv_uid: Optional[str] = None) -> None:
        self._refresh_panel()
        self._refresh_slots()
        self._refresh_inventory(keep_inv_uid)

    def _persist(self) -> None:
        save_state(self.state)

    def _do_farm(self, slot: str) -> None:
        eq = create_equipment(slot)
        self.state.equipment[eq.uid] = eq
        self._persist()
        self._refresh_inventory(keep_uid=eq.uid)
        self._set_status(f"获得：{eq.slot}·{eq.name}")

    def _selected_inv_uid(self) -> Optional[str]:
        sel = self.inv_list.curselection()
        if not sel:
            return None
        return self._inv_uid_map[sel[0]]

    def _do_equip_selected(self) -> None:
        uid = self._selected_inv_uid()
        if not uid:
            messagebox.showinfo("提示", "请先在仓库中选择一件装备。")
            return
        msg = equip(self.state, uid, self.spirit_id)
        if msg.startswith("该装备") or msg.startswith("找不到"):
            messagebox.showwarning("无法装备", msg)
            return
        self._persist()
        self._refresh_all()
        self._set_status(msg)

    def _do_unequip(self, slot: str) -> None:
        msg = unequip(self.state, self.spirit_id, slot)
        self._persist()
        self._refresh_all()
        self._set_status(msg)

    def _do_upgrade_slot(self, slot: str) -> None:
        uid = self.state.loadouts[self.spirit_id][slot]
        if not uid:
            return
        eq = self.state.equipment[uid]
        msg = upgrade_equipment(eq)
        if msg.startswith("该装备"):
            messagebox.showinfo("提示", msg)
            return
        self._persist()
        self._refresh_all()
        self._set_status(msg)

    def _do_upgrade_selected(self) -> None:
        uid = self._selected_inv_uid()
        if not uid:
            messagebox.showinfo("提示", "请先在仓库中选择要升级的装备。")
            return
        eq = self.state.equipment[uid]
        msg = upgrade_equipment(eq)
        if msg.startswith("该装备"):
            messagebox.showinfo("提示", msg)
            return
        self._persist()
        self._refresh_inventory(keep_uid=uid)
        self._refresh_panel()
        self._refresh_slots()
        self._set_status(msg)

    def _on_close(self) -> None:
        self._persist()
        self.destroy()


def main() -> None:
    EquipmentApp().mainloop()


if __name__ == "__main__":
    main()
