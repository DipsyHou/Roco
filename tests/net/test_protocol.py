from __future__ import annotations

import pytest

from roco.net.urls import build_battle_ws_url
from roco.net.protocol import MSG_ERROR, MSG_STATE_UPDATE, err, state_update


@pytest.mark.parametrize(
    ("host", "port", "use_wss", "expected"),
    [
        ("127.0.0.1", "8765", False, "ws://127.0.0.1:8765"),
        ("game.example.com", "", True, "wss://game.example.com"),
        ("game.example.com", "443", True, "wss://game.example.com"),
        ("wss://game.example.com", "8765", False, "wss://game.example.com"),
        ("https://game.example.com", "", False, "wss://game.example.com"),
    ],
)
def test_build_battle_ws_url_normalizes_common_inputs(host, port, use_wss, expected):
    assert build_battle_ws_url(host, port, use_wss=use_wss) == expected


def test_protocol_error_message_shape():
    assert err("bad") == {"type": MSG_ERROR, "message": "bad"}


def test_protocol_state_update_shape():
    message = state_update(
        {"battleId": "b1"},
        your_player_id="p1",
        effective_speeds={"s1": 200},
        room_status="playing",
    )

    assert message == {
        "type": MSG_STATE_UPDATE,
        "state": {"battleId": "b1"},
        "yourPlayerId": "p1",
        "effectiveSpeeds": {"s1": 200},
        "roomStatus": "playing",
    }
