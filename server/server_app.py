"""Desktop UI for the online battle server."""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from typing import Optional

try:
    import websockets  # noqa: F401
except ImportError as exc:  # pragma: no cover
    raise SystemExit("请先安装 websockets：pip install websockets") from exc

from server.ws_server import serve_until_stopped

UI_FONT = ("Microsoft YaHei UI", 10)
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = "8765"


class _QueueLogHandler(logging.Handler):
    def __init__(self, log_queue: queue.Queue[str]) -> None:
        super().__init__()
        self._log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._log_queue.put_nowait(self.format(record))
        except Exception:
            pass


class ServerRunner:
    """Run WebSocket server on a background thread with asyncio stop event."""

    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop: Optional[asyncio.Event] = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, host: str, port: int) -> None:
        if self.is_running:
            return
        self._thread = threading.Thread(
            target=self._run,
            args=(host, port),
            daemon=True,
            name="roco-ws-server",
        )
        self._thread.start()

    def stop(self) -> None:
        if self._loop and self._stop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._stop.set)
        if self._thread:
            self._thread.join(timeout=5.0)
        self._thread = None
        self._loop = None
        self._stop = None

    def _run(self, host: str, port: int) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._stop = asyncio.Event()
        try:
            self._loop.run_until_complete(serve_until_stopped(host, port, self._stop))
        finally:
            self._loop.close()


class ServerDesktopApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.tk.call("encoding", "system", "utf-8")
        self.title("Roco 联机对战 · 服务端")
        self.resizable(True, True)
        self.geometry("520x420")
        self.minsize(440, 360)

        self._runner = ServerRunner()
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._setup_logging()

        wrap = ttk.Frame(self, padding=12)
        wrap.pack(fill=tk.BOTH, expand=True)

        cfg = ttk.LabelFrame(wrap, text="监听配置", padding=10)
        cfg.pack(fill=tk.X)

        ttk.Label(cfg, text="监听地址", font=UI_FONT).grid(row=0, column=0, sticky="w")
        self.host_var = tk.StringVar(value=DEFAULT_HOST)
        host_row = ttk.Frame(cfg)
        host_row.grid(row=0, column=1, sticky="w", pady=2)
        self._host_entry = ttk.Entry(host_row, textvariable=self.host_var, width=18)
        self._host_entry.pack(side=tk.LEFT)
        ttk.Button(host_row, text="本机", width=5, command=lambda: self.host_var.set("127.0.0.1")).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        ttk.Button(host_row, text="全部网卡", width=8, command=lambda: self.host_var.set("0.0.0.0")).pack(
            side=tk.LEFT, padx=(4, 0)
        )

        ttk.Label(cfg, text="端口", font=UI_FONT).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.port_var = tk.StringVar(value=DEFAULT_PORT)
        self._port_entry = ttk.Entry(cfg, textvariable=self.port_var, width=10)
        self._port_entry.grid(row=1, column=1, sticky="w", pady=(8, 0))


        btn_row = ttk.Frame(wrap)
        btn_row.pack(fill=tk.X, pady=(12, 0))
        self.start_btn = ttk.Button(btn_row, text="启动服务", command=self._on_start)
        self.start_btn.pack(side=tk.LEFT)
        self.stop_btn = ttk.Button(btn_row, text="停止服务", command=self._on_stop, state="disabled")
        self.stop_btn.pack(side=tk.LEFT, padx=(8, 0))

        self.status_var = tk.StringVar(value="未启动")
        ttk.Label(btn_row, textvariable=self.status_var, font=UI_FONT).pack(side=tk.LEFT, padx=(16, 0))

        ttk.Label(wrap, text="运行日志", font=UI_FONT).pack(anchor="w", pady=(12, 4))
        self.log_text = scrolledtext.ScrolledText(
            wrap, height=14, wrap="word", state="disabled", font=("Consolas", 10)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(120, self._poll_logs)

    def _setup_logging(self) -> None:
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        handler = _QueueLogHandler(self._log_queue)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S"))
        root.handlers.clear()
        root.addHandler(handler)

    def _append_log(self, line: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, line + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _poll_logs(self) -> None:
        while True:
            try:
                line = self._log_queue.get_nowait()
            except queue.Empty:
                break
            self._append_log(line)
        self.after(120, self._poll_logs)

    def _parse_config(self) -> tuple[str, int]:
        host = self.host_var.get().strip() or DEFAULT_HOST
        port_str = self.port_var.get().strip() or DEFAULT_PORT
        try:
            port = int(port_str)
        except ValueError as exc:
            raise ValueError("端口必须是数字") from exc
        if not (1 <= port <= 65535):
            raise ValueError("端口范围应为 1~65535")
        return host, port

    def _set_running_ui(self, running: bool) -> None:
        state = "disabled" if running else "normal"
        self._host_entry.configure(state=state)
        self._port_entry.configure(state=state)
        self.start_btn.configure(state="disabled" if running else "normal")
        self.stop_btn.configure(state="normal" if running else "disabled")

    def _on_start(self) -> None:
        try:
            host, port = self._parse_config()
        except ValueError as exc:
            messagebox.showerror("配置错误", str(exc), parent=self)
            return
        if self._runner.is_running:
            return
        self._runner.start(host, port)
        self._set_running_ui(True)
        self.status_var.set(f"运行中  ws://{host}:{port}")
        logging.info("服务已启动")

    def _on_stop(self) -> None:
        if not self._runner.is_running:
            return
        self._runner.stop()
        self._set_running_ui(False)
        self.status_var.set("已停止")
        logging.info("服务已停止")

    def _on_close(self) -> None:
        if self._runner.is_running:
            if not messagebox.askyesno("退出", "服务仍在运行，确定退出并停止服务？", parent=self):
                return
            self._runner.stop()
        self.destroy()


def main() -> None:
    app = ServerDesktopApp()
    app.mainloop()


if __name__ == "__main__":
    main()
