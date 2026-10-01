"""WebSocket connection manager for QA-FRAMEWORK Dashboard."""

from typing import Dict, List
from fastapi import WebSocket
from starlette.websockets import WebSocketState
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time notifications."""

    def __init__(self):
        # Map of user_id -> list of websocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept (when still pending) and register a new WebSocket connection."""
        # F-3: the endpoint may have already accepted the handshake to read
        # the first auth message; a second accept() would crash the handler.
        if websocket.application_state == WebSocketState.CONNECTING:
            await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = []

        self.active_connections[user_id].append(websocket)
        logger.info(
            f"WebSocket connected for user {user_id}. Total connections: {len(self.active_connections[user_id])}"
        )

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)

            # Clean up empty lists
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_personal_message(self, message: dict, user_id: int):
        """Send a message to all connections of a specific user."""
        if user_id not in self.active_connections:
            return

        message_json = json.dumps(message)
        disconnected = []

        for connection in self.active_connections[user_id]:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                disconnected.append(connection)

        # Clean up disconnected sockets
        for connection in disconnected:
            self.disconnect(connection, user_id)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected users."""
        message_json = json.dumps(message)

        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)

    async def send_notification(self, user_id: int, notification: dict):
        """Send a notification to a specific user."""
        await self.send_personal_message(
            {"type": "notifications:new", "notification": notification}, user_id
        )

    def get_connection_count(self, user_id: int) -> int:
        """Get the number of active connections for a user."""
        return len(self.active_connections.get(user_id, []))

    def get_total_connections(self) -> int:
        """Get the total number of active connections."""
        return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
manager = ConnectionManager()
