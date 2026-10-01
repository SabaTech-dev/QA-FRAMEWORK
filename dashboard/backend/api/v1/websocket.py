"""WebSocket routes for QA-FRAMEWORK Dashboard.

F-3 hardening (OWASP API4:2023): HTTP rate-limit middleware does not apply
to WebSockets, so this endpoint authenticates during the handshake and caps
concurrent pre-auth sockets per source IP:

- ``token`` query param: verified BEFORE the handshake completes; a bad
  token rejects the handshake itself (close 4401, no socket established).
- Otherwise the first message must be ``{"type": "auth", "token": ...}``
  within ``WS_PREAUTH_TIMEOUT`` seconds (``asyncio.wait_for``); timeout
  closes with 4408, missing/invalid auth closes with 4401.
- At most ``WS_MAX_CONN_PER_IP`` concurrent sockets per peer IP (close
  1008); the slot is released in the handler's ``finally``. The peer
  address is ``scope["client"]`` only — X-Forwarded-For is
  client-controlled (see F-2) and is deliberately not trusted here.
"""

import asyncio
import os
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from services.auth_service import verify_token
from core.logging_config import get_logger
from websocket.manager import manager

logger = get_logger(__name__)

router = APIRouter(tags=["websocket"])

# Read at import time; tests monkeypatch the module attributes.
WS_PREAUTH_TIMEOUT = float(os.getenv("WS_PREAUTH_TIMEOUT_SECONDS", "10"))
WS_MAX_CONN_PER_IP = int(os.getenv("WS_MAX_CONN_PER_IP", "10"))

# ponytail: per-process in-memory counter; move to Redis when multiple workers
_ip_conn_count: Dict[str, int] = {}


def _client_ip(websocket: WebSocket) -> str:
    """Direct peer address (uvicorn --proxy-headers rewrites it behind a proxy)."""
    if websocket.client and websocket.client.host:
        return websocket.client.host
    return "unknown"


@router.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time notifications."""
    ip = _client_ip(websocket)

    if _ip_conn_count.get(ip, 0) >= WS_MAX_CONN_PER_IP:
        logger.warning(
            "WS connection refused, per-IP limit reached",
            client_ip=ip,
            limit=WS_MAX_CONN_PER_IP,
        )
        await websocket.close(code=1008, reason="Too many connections")
        return

    _ip_conn_count[ip] = _ip_conn_count.get(ip, 0) + 1
    user_id = None

    try:
        token = websocket.query_params.get("token")
        if token:
            # Handshake auth: verify before completing the handshake.
            user = await verify_token(token)
            if user is None:
                await websocket.close(code=4401, reason="Invalid token")
                return
        else:
            # First-message auth, bounded by the pre-auth timeout.
            await websocket.accept()
            try:
                auth_message = await asyncio.wait_for(
                    websocket.receive_json(), timeout=WS_PREAUTH_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.warning("WS pre-auth timeout", client_ip=ip)
                await websocket.close(code=4408, reason="Authentication timeout")
                return

            if (
                not isinstance(auth_message, dict)
                or auth_message.get("type") != "auth"
                or not auth_message.get("token")
            ):
                await websocket.close(code=4401, reason="Authentication required")
                return

            user = await verify_token(auth_message.get("token"))
            if user is None:
                await websocket.close(code=4401, reason="Invalid token")
                return

        user_id = user.id

        # Register connection (accepts the handshake if still pending).
        await manager.connect(websocket, user_id)

        await websocket.send_json(
            {
                "type": "connected",
                "message": "WebSocket connected successfully",
                "user_id": user_id,
            }
        )

        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_json()

            # Handle ping/pong for keepalive
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

            # Handle subscription to specific channels
            elif data.get("type") == "subscribe":
                channel = data.get("channel")
                await websocket.send_json({"type": "subscribed", "channel": channel})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", user_id=user_id)

    except Exception as e:
        logger.error("WebSocket error", error=str(e), user_id=user_id)
        if websocket.application_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
            except Exception:  # socket already gone
                pass

    finally:
        if user_id is not None:
            manager.disconnect(websocket, user_id)
        remaining = _ip_conn_count.get(ip, 1) - 1
        if remaining > 0:
            _ip_conn_count[ip] = remaining
        else:
            _ip_conn_count.pop(ip, None)
