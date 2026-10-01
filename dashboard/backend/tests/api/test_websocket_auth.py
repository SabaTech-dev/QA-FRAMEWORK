"""WebSocket /ws/notifications authentication hardening (F-3, card cbfac469).

Security finding fixed here:

- F-3 (CVSS 5.3 Medium, OWASP API4:2023): the endpoint called ``accept()``
  before any authentication and waited for the auth message without a
  timeout. HTTP rate-limit middleware does not apply to WebSockets, so an
  anonymous client could hold sockets open indefinitely and exhaust the
  connection manager.

Expected behavior now:

- Authentication happens in the handshake: a ``token`` query param
  (verified before the handshake completes) or the first message, bounded
  by a pre-auth timeout (``asyncio.wait_for``).
- Missing/invalid auth closes with 4401; pre-auth timeout closes with 4408;
  the per-IP concurrency cap (``WS_MAX_CONN_PER_IP``) rejects the N+1th
  concurrent socket from one IP with 1008 before accepting it.
- The per-IP slot is released when the handler exits (disconnect included).

The module-level constants are monkeypatched instead of env vars so tests
do not depend on import-time environment state.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import api.v1.websocket as ws_module
from api.v1.websocket import router

WS_PATH = "/ws/notifications"


def _user_mock(user_id: int = 1) -> AsyncMock:
    return AsyncMock(return_value=SimpleNamespace(id=user_id))


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_ip_counter():
    """Isolate the module-level per-IP counter between tests."""
    ws_module._ip_conn_count.clear()
    yield
    ws_module._ip_conn_count.clear()


def test_ws_hardening_defaults():
    """Sane defaults: 10s pre-auth timeout, 10 concurrent sockets per IP."""
    assert ws_module.WS_MAX_CONN_PER_IP == 10
    assert ws_module.WS_PREAUTH_TIMEOUT == 10.0


def test_ws_no_auth_times_out_and_closes_4408(client, monkeypatch):
    """(a) Anonymous socket that never authenticates is closed on timeout."""
    monkeypatch.setattr(ws_module, "WS_PREAUTH_TIMEOUT", 0.2)
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(WS_PATH) as ws:
            # Block until the server-side timeout closes the socket.
            ws.receive_json()
    assert exc.value.code == 4408


def test_ws_auth_via_first_message_connects_and_works(client, monkeypatch):
    """(b) Valid auth in the first message completes the handshake."""
    monkeypatch.setattr(ws_module, "verify_token", _user_mock(user_id=7))
    with client.websocket_connect(WS_PATH) as ws:
        ws.send_json({"type": "auth", "token": "valid-token"})
        welcome = ws.receive_json()
        assert welcome["type"] == "connected"
        assert welcome["user_id"] == 7

        ws.send_json({"type": "ping"})
        assert ws.receive_json() == {"type": "pong"}


def test_ws_auth_via_query_param_connects(client, monkeypatch):
    """(b') Handshake token: auth resolves before the socket is registered."""
    monkeypatch.setattr(ws_module, "verify_token", _user_mock(user_id=3))
    with client.websocket_connect(f"{WS_PATH}?token=valid-token") as ws:
        welcome = ws.receive_json()
        assert welcome["type"] == "connected"
        assert welcome["user_id"] == 3

        ws.send_json({"type": "subscribe", "channel": "executions"})
        assert ws.receive_json() == {"type": "subscribed", "channel": "executions"}


def test_ws_invalid_first_message_token_closes_4401(client, monkeypatch):
    """Invalid token in the first message closes with 4401."""
    monkeypatch.setattr(ws_module, "verify_token", AsyncMock(return_value=None))
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(WS_PATH) as ws:
            ws.send_json({"type": "auth", "token": "bad-token"})
            ws.receive_json()
    assert exc.value.code == 4401


def test_ws_non_auth_first_message_closes_4401(client):
    """A first message that is not an auth frame closes with 4401."""
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(WS_PATH) as ws:
            ws.send_json({"type": "ping"})
            ws.receive_json()
    assert exc.value.code == 4401


def test_ws_invalid_query_token_rejected_before_accept(client, monkeypatch):
    """Invalid handshake token: the handshake itself is rejected with 4401."""
    monkeypatch.setattr(ws_module, "verify_token", AsyncMock(return_value=None))
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"{WS_PATH}?token=bad-token"):
            pass
    assert exc.value.code == 4401


def test_ws_per_ip_limit_rejects_nth_plus_one(client, monkeypatch):
    """(c) WS_MAX_CONN_PER_IP concurrent sockets per IP; the N+1th gets 1008."""
    monkeypatch.setattr(ws_module, "WS_MAX_CONN_PER_IP", 2)
    monkeypatch.setattr(ws_module, "verify_token", _user_mock(user_id=1))
    with client.websocket_connect(f"{WS_PATH}?token=t") as ws1:
        assert ws1.receive_json()["type"] == "connected"
        with client.websocket_connect(f"{WS_PATH}?token=t") as ws2:
            assert ws2.receive_json()["type"] == "connected"

            with pytest.raises(WebSocketDisconnect) as exc:
                with client.websocket_connect(f"{WS_PATH}?token=t"):
                    pass
            assert exc.value.code == 1008


def test_ws_limit_counts_pre_auth_sockets(client, monkeypatch):
    """Pre-auth sockets count towards the cap: anonymous exhaustion is bounded."""
    monkeypatch.setattr(ws_module, "WS_MAX_CONN_PER_IP", 1)
    with client.websocket_connect(WS_PATH) as ws1:  # accepted, awaiting auth
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(WS_PATH):
                pass
        assert exc.value.code == 1008


def test_ws_disconnect_frees_slot(client, monkeypatch):
    """(d) Closing a connection releases its per-IP slot immediately."""
    monkeypatch.setattr(ws_module, "WS_MAX_CONN_PER_IP", 1)
    monkeypatch.setattr(ws_module, "verify_token", _user_mock(user_id=5))
    with client.websocket_connect(f"{WS_PATH}?token=t") as ws1:
        assert ws1.receive_json()["type"] == "connected"

    # Slot freed by the disconnect -> a new connection from the same IP works.
    with client.websocket_connect(f"{WS_PATH}?token=t") as ws2:
        assert ws2.receive_json()["type"] == "connected"


def test_ws_counter_empty_after_handler_exit(client, monkeypatch):
    """The per-IP bookkeeping leaves no residue once the socket is gone."""
    monkeypatch.setattr(ws_module, "verify_token", _user_mock(user_id=9))
    with client.websocket_connect(f"{WS_PATH}?token=t"):
        pass
    assert ws_module._ip_conn_count == {}
