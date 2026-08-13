"""WebSocket client for online battles (background thread + main-thread callbacks)."""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Any, Callable, Dict, Optional

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    from websockets.exceptions import ConnectionClosed
except ImportError:  # pragma: no cover
    websockets = None  # type: ignore[assignment]
    WebSocketClientProtocol = Any  # type: ignore[misc,assignment]
    ConnectionClosed = Exception  # type: ignore[misc,assignment]


OnMessage = Callable[[Dict[str, Any]], None]
OnDisconnect = Callable[[], None]

# 对战计算可能阻塞数秒；放宽心跳避免 WSL/慢机器误判断线
WS_PING_INTERVAL = 30
WS_PING_TIMEOUT = 120


class BattleNetClient:
    def __init__(
        self,
        url: str,
        on_message: OnMessage,
        on_disconnect: Optional[OnDisconnect] = None,
    ) -> None:
        self.url = url
        self.on_message = on_message
        self.on_disconnect = on_disconnect
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ws: Optional[WebSocketClientProtocol] = None
        self._connected = threading.Event()
        self._stop = threading.Event()

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set() and self._loop is not None and self._loop.is_running()

    def start(self) -> None:
        if websockets is None:
            raise RuntimeError("请先安装 websockets：pip install websockets")
        if self._thread and self._thread.is_alive() and self.is_connected:
            return
        self._stop.clear()
        self._connected.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        if not self._connected.wait(timeout=12.0):
            raise TimeoutError(f"连接服务器超时：{self.url}")

    def close(self) -> None:
        self._stop.set()
        self._connected.clear()
        if self._loop and self._loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop).result(timeout=3)
            except Exception:
                pass

    def send(self, payload: Dict[str, Any]) -> None:
        if not self.is_connected:
            raise RuntimeError("与服务器连接已断开，请从菜单重新进入联机大厅")
        assert self._loop is not None
        try:
            fut = asyncio.run_coroutine_threadsafe(self._send(payload), self._loop)
            fut.result(timeout=10)
        except RuntimeError as exc:
            if "Event loop is closed" in str(exc):
                self._mark_disconnected()
                raise RuntimeError("与服务器连接已断开，请从菜单重新进入联机大厅") from exc
            raise

    def _mark_disconnected(self) -> None:
        was_connected = self._connected.is_set()
        self._connected.clear()
        self._ws = None
        if was_connected and self.on_disconnect:
            self.on_disconnect()

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main())
        finally:
            self._connected.clear()
            self._ws = None
            if not self._loop.is_closed():
                self._loop.close()

    async def _main(self) -> None:
        try:
            async with websockets.connect(
                self.url,
                ping_interval=WS_PING_INTERVAL,
                ping_timeout=WS_PING_TIMEOUT,
                close_timeout=5,
            ) as ws:
                self._ws = ws
                self._connected.set()
                while not self._stop.is_set():
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    except asyncio.TimeoutError:
                        continue
                    except ConnectionClosed:
                        break
                    except Exception:
                        break
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if self.on_message:
                        self.on_message(msg)
        finally:
            self._mark_disconnected()

    async def _send(self, payload: Dict[str, Any]) -> None:
        if self._ws:
            await self._ws.send(json.dumps(payload, ensure_ascii=False))

    async def _shutdown(self) -> None:
        if self._ws:
            await self._ws.close()
