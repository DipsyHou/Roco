"""Online desktop battle app."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, List, Optional

from roco.apps.desktop.app import DesktopGameApp
from roco.apps.desktop.constants import UI_FONT
from roco.apps.desktop.helpers import center_on_parent
from roco.core.battle.types import BattlePhase, BattleSpirit
from roco.core.battle.engine import MAX_TEAM_SIZE, MIN_TEAM_SIZE
from roco.net.client import BattleNetClient
from roco.net.protocol import (
    MSG_ACTION_RESULT,
    MSG_BATTLE_STARTED,
    MSG_CREATE_ROOM,
    MSG_ERROR,
    MSG_JOIN_ROOM,
    MSG_READY,
    MSG_ROOM_JOINED,
    MSG_STATE_UPDATE,
)
from roco.net.remote_engine import RemoteBattleEngine
from roco.net.serialize import SchemaVersionError
from roco.net.urls import build_battle_ws_url
from roco.core.spirits import ALL_SPIRITS


class OnlineLobbyWindow(tk.Toplevel):
    _TEAM_COLS = 4
    _SELECT_BORDER = "#2563eb"

    def __init__(self, master: DesktopGameApp, on_connected: Callable[..., None]) -> None:
        super().__init__(master)
        self.title("联机大厅")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self._app = master
        self._on_connected = on_connected
        self._client: Optional[BattleNetClient] = None
        self._room_id: Optional[str] = None
        self._slot: Optional[str] = None
        self._selected_order: List[int] = []
        self._selected_set: set[int] = set()
        self._spirit_tiles: Dict[int, tk.Frame] = {}
        self._order_badges: Dict[int, tk.Label] = {}

        wrap = ttk.Frame(self, padding=12)
        wrap.pack(fill=tk.BOTH, expand=True)

        ttk.Label(wrap, text="服务器地址", font=UI_FONT).grid(row=0, column=0, sticky="nw")
        self.host_var = tk.StringVar(value="127.0.0.1")
        self.port_var = tk.StringVar(value="8765")
        self.use_wss_var = tk.BooleanVar(value=False)
        host_col = ttk.Frame(wrap)
        host_col.grid(row=0, column=1, sticky="w", pady=2)
        host_row = ttk.Frame(host_col)
        host_row.pack(anchor="w")
        host_entry = ttk.Entry(host_row, textvariable=self.host_var, width=28)
        host_entry.pack(side=tk.LEFT)
        host_entry.bind("<KeyRelease>", lambda _e: self._refresh_url_hint())
        self._port_label = ttk.Label(host_row, text=":")
        self._port_label.pack(side=tk.LEFT)
        self._port_entry = ttk.Entry(host_row, textvariable=self.port_var, width=6)
        self._port_entry.pack(side=tk.LEFT)
        self._port_entry.bind("<KeyRelease>", lambda _e: self._refresh_url_hint())
        ttk.Checkbutton(
            host_col,
            text="启用 wss 协议",
            variable=self.use_wss_var,
            command=self._on_wss_toggle,
        ).pack(anchor="w", pady=(4, 0))
        self.url_hint_var = tk.StringVar(value="")
        ttk.Label(host_col, textvariable=self.url_hint_var, font=UI_FONT).pack(anchor="w", pady=(2, 0))
        self._refresh_url_hint()

        ttk.Label(wrap, text="房间号", font=UI_FONT).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.room_var = tk.StringVar(value="")
        ttk.Entry(wrap, textvariable=self.room_var, width=24).grid(row=1, column=1, sticky="w", pady=(8, 0))

        btn_row = ttk.Frame(wrap)
        btn_row.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Button(btn_row, text="创建房间", command=self._create_room).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="加入房间", command=self._join_room).pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="未连接")
        ttk.Label(wrap, textvariable=self.status_var, font=UI_FONT).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )

        ttk.Label(
            wrap,
            text=f"选择你的阵容（最多{MAX_TEAM_SIZE} 只，点击顺序即上场顺序）",
            font=UI_FONT,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 4))

        team_wrap = ttk.Frame(wrap)
        team_wrap.grid(row=5, column=0, columnspan=2, sticky="ew")
        for idx, tpl in enumerate(ALL_SPIRITS):
            row, col = divmod(idx, self._TEAM_COLS)
            self._build_spirit_tile(team_wrap, idx, tpl, row, col)

        bottom = ttk.Frame(wrap)
        bottom.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.ready_btn = ttk.Button(bottom, text="准备并开始", command=self._send_ready, state="disabled")
        self.ready_btn.pack(side=tk.LEFT, padx=8)
        ttk.Button(bottom, text="取消", command=self.destroy).pack(side=tk.LEFT)

        self.update_idletasks()
        center_on_parent(self, master)

    def _build_spirit_tile(
        self,
        parent: ttk.Frame,
        idx: int,
        tpl,
        row: int,
        col: int,
    ) -> None:
        cell = tk.Frame(parent, padx=2, pady=2, relief=tk.RAISED, borderwidth=1)
        cell.grid(row=row, column=col, padx=4, pady=4)
        self._spirit_tiles[idx] = cell

        img = self._app._load_avatar(tpl.name)
        if img:
            img_lbl = tk.Label(cell, image=img, cursor="hand2")
            img_lbl.image = img
        else:
            img_lbl = tk.Label(cell, text="无图", width=8, height=4, cursor="hand2")
        img_lbl.pack()
        name_lbl = tk.Label(cell, text=tpl.name, font=UI_FONT, cursor="hand2")
        name_lbl.pack(pady=(2, 0))

        # 顺序标号必须在图片之后创建并置顶，否则会被 pack 的控件挡住
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
        self._order_badges[idx] = badge

        for widget in (cell, img_lbl, name_lbl, badge):
            widget.bind("<Button-1>", lambda _e, i=idx: self._toggle_spirit(i))

    def _toggle_spirit(self, idx: int) -> None:
        if idx in self._selected_set:
            self._selected_set.remove(idx)
            self._selected_order[:] = [i for i in self._selected_order if i != idx]
        else:
            if len(self._selected_order) >= MAX_TEAM_SIZE:
                messagebox.showwarning(
                    "阵容已满",
                    f"最多选择 {MAX_TEAM_SIZE} 只精灵，请先取消一只再选。",
                    parent=self,
                )
                return
            self._selected_set.add(idx)
            self._selected_order.append(idx)
        self._refresh_team_selection_ui()

    def _refresh_team_selection_ui(self) -> None:
        order_map = {spirit_idx: pos + 1 for pos, spirit_idx in enumerate(self._selected_order)}
        for idx, badge in self._order_badges.items():
            order = order_map.get(idx)
            if order:
                badge.configure(text=str(order))
                badge.place(x=4, y=4, anchor="nw")
                badge.lift()
            else:
                badge.configure(text="")
                badge.place_forget()
        for idx, cell in self._spirit_tiles.items():
            if idx in self._selected_set:
                cell.configure(
                    highlightthickness=2,
                    highlightbackground=self._SELECT_BORDER,
                    highlightcolor=self._SELECT_BORDER,
                )
            else:
                cell.configure(highlightthickness=0)

    def _on_wss_toggle(self) -> None:
        if self.use_wss_var.get():
            if self.port_var.get().strip() in ("", "8765"):
                self.port_var.set("")
        elif not self.port_var.get().strip():
            self.port_var.set("8765")
        self._refresh_url_hint()

    def _refresh_url_hint(self) -> None:
        try:
            url = build_battle_ws_url(
                self.host_var.get(),
                self.port_var.get(),
                use_wss=self.use_wss_var.get(),
            )
            self.url_hint_var.set(f"将连接: {url}")
        except ValueError as exc:
            self.url_hint_var.set(f"地址无效: {exc}")

    def _ws_url(self) -> str:
        return build_battle_ws_url(
            self.host_var.get(),
            self.port_var.get(),
            use_wss=self.use_wss_var.get(),
        )

    def _connect(self) -> BattleNetClient:
        if self._client and self._client.is_connected:
            return self._client
        client = BattleNetClient(
            self._ws_url(),
            self._on_net_message,
            on_disconnect=self._on_disconnect,
        )
        client.start()
        self._client = client
        return client

    def _on_disconnect(self) -> None:
        if self.winfo_exists():
            self.status_var.set("连接已断开")

    def _on_net_message(self, msg: Dict[str, Any]) -> None:
        self.after(0, lambda m=msg: self._handle_net_message(m))

    def _enter_battle(self, msg: Dict[str, Any]) -> None:
        if not self._client or not self._room_id or not self._slot:
            return
        state = msg.get("state")
        if not state:
            return
        player_id = "p1" if self._slot == "p1" else "p2"
        try:
            eng = RemoteBattleEngine(self._client, player_id)
            eng.apply_server_snapshot(state, msg.get("effectiveSpeeds") or {})
        except Exception as exc:
            messagebox.showerror(
                "进入战斗失败",
                f"无法加载战斗状态：{exc}",
                parent=self,
            )
            self.ready_btn.configure(state="normal")
            return
        self.destroy()
        self._on_connected(self._client, eng, self._room_id, self._slot)

    def _handle_net_message(self, msg: Dict[str, Any]) -> None:
        mtype = msg.get("type")
        if mtype == MSG_ERROR:
            messagebox.showwarning("联机", msg.get("message", "未知错误"), parent=self)
            if self._slot:
                self.ready_btn.configure(state="normal")
            return
        if mtype == MSG_ROOM_JOINED:
            self._room_id = msg.get("roomId")
            self._slot = msg.get("slot")
            self.room_var.set(self._room_id or "")
            role = "Player 1" if self._slot == "p1" else "Player 2"
            self.status_var.set(f"已加入房间 {self._room_id}（{role}）")
            self.ready_btn.configure(state="normal")
            return
        if mtype == MSG_STATE_UPDATE and msg.get("state") is None:
            ready = msg.get("ready") or []
            self._update_lobby_ready_status(ready)
            return
        if mtype in (MSG_BATTLE_STARTED, MSG_STATE_UPDATE):
            if msg.get("state"):
                self._enter_battle(msg)
            return

    def _create_room(self) -> None:
        try:
            client = self._connect()
            client.send({"type": MSG_CREATE_ROOM})
            self.status_var.set("正在创建房间…")
        except Exception as exc:
            messagebox.showerror("连接失败", str(exc), parent=self)

    def _join_room(self) -> None:
        room_id = self.room_var.get().strip()
        if not room_id:
            messagebox.showwarning("提示", "请输入房间号", parent=self)
            return
        try:
            client = self._connect()
            client.send({"type": MSG_JOIN_ROOM, "roomId": room_id})
            self.status_var.set(f"正在加入房间 {room_id}…")
        except Exception as exc:
            messagebox.showerror("连接失败", str(exc), parent=self)

    def _team_ids(self) -> List[str]:
        return [ALL_SPIRITS[i].id for i in self._selected_order]

    def _update_lobby_ready_status(self, ready: List[str]) -> None:
        slot = self._slot or ""
        me_ready = slot in ready
        opp = "p2" if slot == "p1" else "p1"
        opp_ready = opp in ready
        my_label = "Player 1" if slot == "p1" else "Player 2"
        opp_label = "Player 2" if slot == "p1" else "Player 1"
        me_txt = "已准备" if me_ready else "未准备（需点「准备并开始」）"
        opp_txt = "已准备" if opp_ready else "未准备"
        self.status_var.set(
            
                f"房间 {self._room_id} | 你({my_label}) {me_txt} | 对手({opp_label}) {opp_txt}"
            
        )
        self.ready_btn.configure(state="disabled" if me_ready else "normal")

    def _send_ready(self) -> None:
        if not self._client:
            return
        ids = self._team_ids()
        if not (MIN_TEAM_SIZE <= len(ids) <= MAX_TEAM_SIZE):
            messagebox.showwarning(
                "阵容无效",
                f"请选择 {MIN_TEAM_SIZE}~{MAX_TEAM_SIZE} 只精灵。",
                parent=self,
            )
            return
        self._client.send({"type": MSG_READY, "templateIds": ids})
        self.ready_btn.configure(state="disabled")
        self.status_var.set("已发送准备，等待服务器确认…")


class OnlineDesktopGameApp(DesktopGameApp):
    def __init__(self) -> None:
        self._net_client: Optional[BattleNetClient] = None
        self._my_slot: Optional[str] = None
        self._my_player_id: Optional[str] = None
        self._refresh_pending = False
        self._dead_sync_requested = False
        super().__init__()
        self.title("Roco Online")
        # Parent defaults to local vs-AI; online battles are always human vs human.
        self.vs_ai = False
        self._cancel_ai_job()

    def _schedule_ai_turn(self) -> None:
        """Online never drives an AI client; the remote player acts via the server."""
        self._cancel_ai_job()

    def _build_header_buttons(self, top: ttk.Frame) -> None:
        ttk.Button(top, text="离开房间", command=self._leave_room).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(top, text="战斗日志", command=self._show_battle_log).pack(side=tk.LEFT, padx=(0, 8))

    def _leave_room(self) -> None:
        if not messagebox.askyesno("离开房间", "确定离开当前房间并返回联机大厅？", parent=self):
            return
        self._open_lobby()

    def _start_default_battle(self) -> None:
        self._open_lobby()

    def _open_team_selector(self) -> None:
        self._open_lobby()

    def _open_lobby(self) -> None:
        if self._net_client:
            try:
                self._net_client.close()
            except Exception:
                pass
            self._net_client = None
        self.eng = None
        self._clear_log_widget()
        self.header_var.set("请连接联机服务器")
        self._clear_action_row()
        OnlineLobbyWindow(self, self._on_lobby_connected)

    def _on_lobby_connected(
        self,
        client: BattleNetClient,
        eng: RemoteBattleEngine,
        room_id: str,
        slot: str,
    ) -> None:
        self._net_client = client
        client.on_message = self._on_net_message
        client.on_disconnect = lambda: self.after(0, self._handle_net_disconnect)
        self._my_slot = slot
        self._my_player_id = eng.my_player_id
        self.eng = eng
        self.vs_ai = False
        self._cancel_ai_job()
        self.p1 = "p1"
        self.p2 = "p2"
        pd = eng.state.players.get(self._my_player_id)
        if pd and pd.spirits:
            self.selected_spirit_id = pd.spirits[0].unique_id
        my_label = "Player 1" if slot == "p1" else "Player 2"
        self.header_var.set(f"联机房间 {room_id} | 你是 {my_label} | 加载界面…")
        self.action_hint.set("正在进入战斗…")
        self.update_idletasks()
        self.after(1, self._refresh)

    def _maybe_request_dead_actor_sync(self, eng: RemoteBattleEngine) -> None:
        if eng.state.phase == BattlePhase.finished or self._dead_sync_requested:
            return
        actor = eng.find_spirit_anywhere(eng.state.active_actor_id or "")
        if actor and not actor.is_alive:
            self._dead_sync_requested = True
            eng.ensure_active_turn_begun()

    # --- policy hooks (see DesktopGameApp) --------------------------------
    #
    # ``self.eng`` here is always None (in the lobby) or a RemoteBattleEngine:
    # both entry points to the parent's local ``_start_battle`` are overridden
    # to open the lobby instead. So these only need a None guard.

    def _engine_is_authoritative(self) -> bool:
        """The server owns the engine; this app renders a synced mirror."""
        return False

    def _ally_player_id(self) -> str:
        """Render this client's own seat as "我方", even when seated as p2."""
        return self._my_player_id or self.p1

    def _before_refresh(self) -> None:
        eng = self.eng
        if eng is not None:
            self._maybe_request_dead_actor_sync(eng)

    def _turn_block_reason(self, actor: BattleSpirit) -> Optional[str]:
        eng = self.eng
        if eng is None or eng.is_my_turn():
            return None
        who = "Player 1" if actor.owner_id == self.p1 else "Player 2"
        return f"等待 {who}：{actor.name}"

    def _header_text(self, actor: Optional[BattleSpirit]) -> str:
        eng = self.eng
        if eng is None or not self._my_player_id:
            return super()._header_text(actor)
        my_label = "Player 1" if self._my_player_id == self.p1 else "Player 2"
        if eng.state.phase == BattlePhase.finished:
            return f"你是 {my_label} | 战斗结束"
        if actor is None:
            return f"你是 {my_label} | 等待行动…"
        cur_label = "Player 1" if actor.owner_id == self.p1 else "Player 2"
        return (
            f"你是 {my_label} | 行动 #{eng.state.action_count + 1} | "
            f"当前 {cur_label}: {actor.name}"
        )

    def _after_submit(self) -> None:
        # The server pushes authoritative state; re-rendering now would show a
        # stale mirror and fight the debounced refresh in _on_net_push.
        pass

    def _handle_net_disconnect(self) -> None:
        self.eng = None
        self._clear_action_row()
        self.action_hint.set("与服务器连接已断开")
        self.header_var.set("连接已断开")
        messagebox.showwarning(
            "联机",
            "与服务器连接已断开。\n请点击「离开房间」重新进入联机大厅。",
        )

    def _on_net_message(self, msg: Dict[str, Any]) -> None:
        self.after(0, lambda m=msg: self._on_net_push(m))

    def _on_net_push(self, msg: Dict[str, Any]) -> None:
        mtype = msg.get("type")
        if mtype == MSG_ERROR:
            messagebox.showwarning("联机", msg.get("message", "未知错误"))
            return
        if mtype == MSG_ACTION_RESULT and not msg.get("ok"):
            self._pending_tengjiao_serve = None
            messagebox.showwarning("行动失败", msg.get("message", "无效行动"))
            return
        if mtype == MSG_STATE_UPDATE and isinstance(self.eng, RemoteBattleEngine):
            if msg.get("state"):
                try:
                    self.eng.apply_server_snapshot(
                        msg["state"],
                        msg.get("effectiveSpeeds") or {},
                    )
                except SchemaVersionError as exc:
                    # Keep the last good state rather than rendering a
                    # half-parsed one; the mismatch needs a client update.
                    self._handle_schema_mismatch(str(exc))
                    return
                self._dead_sync_requested = False
            if self._refresh_pending:
                return
            self._refresh_pending = True
            self.after(1, self._refresh_debounced)

    def _handle_schema_mismatch(self, message: str) -> None:
        """Server speaks a newer wire format — stop syncing and tell the user."""
        client = self._net_client
        if client is not None:
            try:
                client.close()
            except Exception:  # noqa: BLE001
                pass
        self._clear_action_row()
        self.action_hint.set("版本不兼容，已断开")
        self.header_var.set("版本不兼容")
        messagebox.showerror("联机", f"{message}\n\n已断开连接，请点击「离开房间」返回大厅。")

    def _refresh_debounced(self) -> None:
        self._refresh_pending = False
        self._refresh()
        from roco.apps.desktop.skill_flows import resume_pending_tengjiao_serve

        resume_pending_tengjiao_serve(self)


def main() -> None:
    app = OnlineDesktopGameApp()
    app.mainloop()


if __name__ == "__main__":
    main()
