"""WebSocket message types for online battles."""

from __future__ import annotations

from typing import Any, Dict


# Client -> server
MSG_CREATE_ROOM = "create_room"
MSG_JOIN_ROOM = "join_room"
MSG_READY = "ready"
MSG_SUBMIT_ACTION = "submit_action"
MSG_SYNC_TURN = "sync_turn"

# Server -> client
MSG_ROOM_JOINED = "room_joined"
MSG_STATE_UPDATE = "state_update"
MSG_BATTLE_STARTED = "battle_started"
MSG_ERROR = "error"
MSG_ACTION_RESULT = "action_result"


def err(message: str) -> Dict[str, Any]:
    return {"type": MSG_ERROR, "message": message}


def state_update(
    state: Dict[str, Any],
    *,
    your_player_id: str,
    effective_speeds: Dict[str, int],
    room_status: str,
) -> Dict[str, Any]:
    return {
        "type": MSG_STATE_UPDATE,
        "state": state,
        "yourPlayerId": your_player_id,
        "effectiveSpeeds": effective_speeds,
        "roomStatus": room_status,
    }
