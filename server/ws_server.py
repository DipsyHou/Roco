"""WebSocket battle server entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from typing import Any, Dict, Optional

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError as exc:  # pragma: no cover
    raise SystemExit("请先安装 websockets：pip install websockets") from exc

from roco.net.protocol import (
    MSG_CREATE_ROOM,
    MSG_JOIN_ROOM,
    MSG_READY,
    MSG_SUBMIT_ACTION,
    MSG_SYNC_TURN,
    MSG_ROOM_JOINED,
    err,
)

from roco.net.transport import send_json as _send_json
from server.room_manager import Room, RoomManager

# 战斗计算在线程池执行；主线程需能响应 WebSocket 心跳
WS_PING_INTERVAL = 30
WS_PING_TIMEOUT = 120

logger = logging.getLogger(__name__)


class ConnectionState:
    def __init__(self) -> None:
        self.slot: Optional[str] = None
        self.room: Optional[Room] = None


MANAGER = RoomManager()


async def handle_message(ws: Any, state: ConnectionState, raw: str) -> None:
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        await _send_json(ws, err("无效 JSON"))
        return

    mtype = msg.get("type")
    if mtype == MSG_CREATE_ROOM:
        room = MANAGER.create_room()
        state.room = room
        state.slot = "p1"
        room.slots["p1"] = ws
        await _send_json(
            ws,
            {
                "type": MSG_ROOM_JOINED,
                "roomId": room.room_id,
                "slot": "p1",
                "status": room.status,
            },
        )
        await room.push_state()
        logger.info("room %s created by p1", room.room_id)
        return

    if mtype == MSG_JOIN_ROOM:
        room_id = (msg.get("roomId") or msg.get("room_id") or "").strip()
        room = MANAGER.get_room(room_id)
        if not room:
            await _send_json(ws, err("房间不存在"))
            return
        for slot_name, sock in room.slots.items():
            if sock is ws:
                state.room = room
                state.slot = slot_name
                await _send_json(
                    ws,
                    {
                        "type": MSG_ROOM_JOINED,
                        "roomId": room.room_id,
                        "slot": slot_name,
                        "status": room.status,
                    },
                )
                await room.push_state()
                logger.info("room %s: %s rejoined", room.room_id, slot_name)
                return
        if "p1" not in room.slots:
            slot = "p1"
        elif "p2" not in room.slots:
            slot = "p2"
        else:
            await _send_json(ws, err("房间已满"))
            return
        state.room = room
        state.slot = slot
        room.slots[slot] = ws
        await _send_json(
            ws,
            {
                "type": MSG_ROOM_JOINED,
                "roomId": room.room_id,
                "slot": slot,
                "status": room.status,
            },
        )
        await room.push_state()
        logger.info("room %s: %s joined", room.room_id, slot)
        return

    room = state.room
    slot = state.slot
    if not room or not slot:
        await _send_json(ws, err("请先创建或加入房间"))
        return

    if mtype == MSG_READY:
        ids = msg.get("templateIds") or msg.get("template_ids")
        if isinstance(ids, list) and ids:
            room.teams[slot] = [str(x) for x in ids]
        if not room.teams.get(slot):
            await _send_json(ws, err("请先选择阵容"))
            return
        room.ready.add(slot)
        logger.info(
            "room %s: %s ready (%d/%d)",
            room.room_id,
            slot,
            len(room.ready),
            len(room.slots),
        )
        err_msg = await room.try_start_battle()
        if err_msg:
            room.ready.discard(slot)
            await room.push_state()
            await _send_json(ws, err_msg)
            logger.warning("room %s: start failed for %s: %s", room.room_id, slot, err_msg)
        elif not room.engine:
            await room.push_state()
        else:
            logger.info("room %s: battle started", room.room_id)
        return

    if mtype == MSG_SYNC_TURN:
        if room.engine:
            await asyncio.to_thread(room._sync_turn_and_dead_skips)
            await room.push_state()
        return

    if mtype == MSG_SUBMIT_ACTION:
        action = msg.get("action") or {}
        result = await room.handle_submit_action(slot, action)
        if result.get("type") == "error":
            await _send_json(ws, result)
        else:
            await _send_json(ws, result)
        return

    await _send_json(ws, err(f"未知消息类型: {mtype}"))


async def ws_handler(ws: Any) -> None:
    state = ConnectionState()
    try:
        async for raw in ws:
            await handle_message(ws, state, raw)
    except ConnectionClosed:
        logger.info("client disconnected")
    finally:
        MANAGER.remove_ws(ws)


async def serve_until_stopped(host: str, port: int, stop: asyncio.Event) -> None:
    async with websockets.serve(
        ws_handler,
        host,
        port,
        ping_interval=WS_PING_INTERVAL,
        ping_timeout=WS_PING_TIMEOUT,
    ):
        logger.info("Roco online server listening on ws://%s:%s", host, port)
        await stop.wait()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Roco online battle server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        asyncio.run(serve_until_stopped(args.host, args.port, asyncio.Event()))
    except KeyboardInterrupt:
        logger.info("server stopped")


if __name__ == "__main__":
    main()
