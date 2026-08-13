"""In-memory rooms hosting authoritative BattleEngine instances."""

from __future__ import annotations

import secrets
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from roco.core.battle.types import ActionType, BattlePhase, player_action_from_dict
from roco.core.battle.rules import MAX_DEAD_ACTOR_SKIPS, MAX_TEAM_SIZE, MIN_TEAM_SIZE
from roco.core.battle.engine import BattleEngine
from roco.net.protocol import (
    MSG_ACTION_RESULT,
    MSG_BATTLE_STARTED,
    MSG_ERROR,
    MSG_STATE_UPDATE,
    err,
    state_update,
)
from roco.net.serialize import state_to_dict
from roco.net.transport import send_json as _send_json
from roco.core.spirits import get_spirit_template
from roco.core.spirits.templates import SpiritTemplate


PLAYER_IDS = ("p1", "p2")
SLOT_TO_PLAYER = {"p1": PLAYER_IDS[0], "p2": PLAYER_IDS[1]}


def _templates_from_ids(ids: List[str]) -> List[SpiritTemplate]:
    out: List[SpiritTemplate] = []
    for sid in ids:
        tpl = get_spirit_template(sid)
        if tpl:
            out.append(tpl)
    return out


@dataclass
class Room:
    room_id: str
    slots: Dict[str, Any] = field(default_factory=dict)  # slot -> websocket
    teams: Dict[str, List[str]] = field(default_factory=dict)
    ready: Set[str] = field(default_factory=set)
    engine: Optional[BattleEngine] = None
    status: str = "waiting"  # waiting | battling | finished
    _lock: threading.Lock = field(default_factory=threading.Lock)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        for ws in self.slots.values():
            if ws is not None:
                await _send_json(ws, payload)

    def _effective_speeds(self) -> Dict[str, int]:
        if not self.engine:
            return {}
        out: Dict[str, int] = {}
        for pid in PLAYER_IDS:
            pd = self.engine.state.players.get(pid)
            if not pd:
                continue
            for spirit in pd.spirits:
                out[spirit.unique_id] = self.engine.get_effective_speed(spirit)
        return out

    async def push_state(self) -> None:
        if not self.engine:
            for slot, ws in self.slots.items():
                if ws is None:
                    continue
                await _send_json(
                    ws,
                    {
                        "type": MSG_STATE_UPDATE,
                        "state": None,
                        "yourPlayerId": SLOT_TO_PLAYER[slot],
                        "effectiveSpeeds": {},
                        "roomStatus": self.status,
                        "teams": self.teams,
                        "ready": list(self.ready),
                    },
                )
            return

        speeds = self._effective_speeds()
        state_dict = state_to_dict(self.engine.state)
        for slot, ws in self.slots.items():
            if ws is None:
                continue
            await _send_json(
                ws,
                state_update(
                    state_dict,
                    your_player_id=SLOT_TO_PLAYER[slot],
                    effective_speeds=speeds,
                    room_status=self.status,
                ),
            )

    def _sync_turn_and_dead_skips(self) -> None:
        if not self.engine or self.engine.state.phase == BattlePhase.finished:
            return
        eng = self.engine
        for _ in range(MAX_DEAD_ACTOR_SKIPS):
            eng.ensure_active_turn_begun()
            actor_id = eng.state.active_actor_id
            if not actor_id:
                break
            actor = eng.find_spirit_anywhere(actor_id)
            if not actor or actor.is_alive:
                break
            ok = eng.submit_action(
                actor.owner_id,
                {
                    "type": ActionType.skip.value,
                    "playerId": actor.owner_id,
                    "actorId": actor.unique_id,
                },
            )
            if not ok:
                eng.advance_past_dead_active()
        if self.engine.state.phase == BattlePhase.finished:
            self.status = "finished"

    def try_start_battle_sync(self) -> Optional[Dict[str, Any]]:
        """开战（同步，可能耗时）。未满足条件时返回 None。"""
        with self._lock:
            if self.engine is not None:
                return None
            if len(self.slots) < 2 or len(self.ready) < 2:
                return None
            for slot in ("p1", "p2"):
                team = self.teams.get(slot) or []
                if not (MIN_TEAM_SIZE <= len(team) <= MAX_TEAM_SIZE):
                    return err(f"{slot} 阵容数量需在 {MIN_TEAM_SIZE}~{MAX_TEAM_SIZE}")

            p1_tpls = _templates_from_ids(self.teams.get("p1") or [])
            p2_tpls = _templates_from_ids(self.teams.get("p2") or [])
            if len(p1_tpls) < MIN_TEAM_SIZE or len(p2_tpls) < MIN_TEAM_SIZE:
                return err("阵容模板无效")

            self.engine = BattleEngine(
                battle_id=str(uuid.uuid4()),
                player1_id=PLAYER_IDS[0],
                player2_id=PLAYER_IDS[1],
                p1_templates=p1_tpls,
                p2_templates=p2_tpls,
            )
            self.status = "battling"
            self._sync_turn_and_dead_skips()
        return None

    async def try_start_battle(self) -> Optional[Dict[str, Any]]:
        import asyncio

        err_result = await asyncio.to_thread(self.try_start_battle_sync)
        if err_result:
            return err_result
        if self.engine:
            await self.broadcast({"type": MSG_BATTLE_STARTED})
            await self.push_state()
        return None

    def process_submit_action_sync(
        self, slot: str, action_raw: Dict[str, Any]
    ) -> Dict[str, Any]:
        with self._lock:
            if not self.engine:
                return err("战斗尚未开始")
            if self.engine.state.phase == BattlePhase.finished:
                return err("战斗已结束")

            player_id = SLOT_TO_PLAYER[slot]
            action = player_action_from_dict(action_raw)
            eng = self.engine
            actor_id = eng.state.active_actor_id
            actor = eng.find_spirit_anywhere(actor_id or "")
            if not actor or actor.owner_id != player_id:
                return err("还没轮到你行动")
            if action.get("actorId") and action.get("actorId") != actor.unique_id:
                return err("行动者与当前回合不一致")

            eng.ensure_active_turn_begun()
            ok = eng.submit_action(player_id, action)
            self._sync_turn_and_dead_skips()
            if self.engine.state.phase == BattlePhase.finished:
                self.status = "finished"
            return {
                "type": MSG_ACTION_RESULT,
                "ok": ok,
                "message": "" if ok else "行动未通过校验",
            }

    async def handle_submit_action(
        self, slot: str, action_raw: Dict[str, Any]
    ) -> Dict[str, Any]:
        import asyncio

        result = await asyncio.to_thread(self.process_submit_action_sync, slot, action_raw)
        if result.get("type") != "error" and self.engine:
            await self.push_state()
        return result


class RoomManager:
    def __init__(self) -> None:
        self.rooms: Dict[str, Room] = {}

    def create_room(self) -> Room:
        room_id = secrets.token_hex(3)
        while room_id in self.rooms:
            room_id = secrets.token_hex(3)
        room = Room(room_id=room_id)
        self.rooms[room_id] = room
        return room

    def get_room(self, room_id: str) -> Optional[Room]:
        return self.rooms.get(room_id)

    def remove_ws(self, ws: Any) -> None:
        for room_id, room in list(self.rooms.items()):
            for slot, sock in list(room.slots.items()):
                if sock is ws:
                    room.slots.pop(slot, None)
                    room.ready.discard(slot)
            # An empty room is unreachable — no socket can rejoin it — so it must
            # be recycled regardless of status. Previously "battling" rooms were
            # kept, leaking one BattleEngine per abandoned match.
            if not room.slots:
                self.rooms.pop(room_id, None)
