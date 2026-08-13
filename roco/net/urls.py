"""WebSocket URL construction/normalization for the online client.

Lives under ``roco.net`` (not the UI package) so protocol tests and non-Tk
callers can build URLs without importing tkinter.
"""

from __future__ import annotations

from urllib.parse import urlparse


def build_battle_ws_url(host: str, port: str, *, use_wss: bool = False) -> str:
    """Build WebSocket URL (local ws://host:8765 or Cloudflare wss://domain)."""
    raw = (host or "").strip()
    if not raw:
        raw = "127.0.0.1"

    lowered = raw.lower()
    if lowered.startswith(("ws://", "wss://", "http://", "https://")):
        return _normalize_pasted_url(raw)

    port_str = (port or "").strip()
    if use_wss:
        if not port_str or port_str in ("443", "80"):
            return f"wss://{raw}"
        return f"wss://{raw}:{port_str}"

    port_str = port_str or "8765"
    return f"ws://{raw}:{port_str}"


def _normalize_pasted_url(raw: str) -> str:
    s = raw.strip()
    low = s.lower()
    if low.startswith("https://"):
        s = "wss://" + s[8:]
    elif low.startswith("http://"):
        s = "ws://" + s[7:]
    parsed = urlparse(s)
    scheme = parsed.scheme.lower()
    if scheme not in ("ws", "wss"):
        raise ValueError(f"不支持的协议: {parsed.scheme}")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("无效服务器地址")
    if parsed.port:
        authority = f"{hostname}:{parsed.port}"
    else:
        authority = hostname
    path = parsed.path or ""
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return f"{scheme}://{authority}{path}"
