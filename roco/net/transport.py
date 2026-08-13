"""Low-level websocket send helpers shared by server and room manager."""

from __future__ import annotations

import json
from typing import Any, Dict


async def send_json(ws: Any, payload: Dict[str, Any]) -> None:
    """Serialize ``payload`` as UTF-8 JSON and send it over ``ws``."""
    await ws.send(json.dumps(payload, ensure_ascii=False))
