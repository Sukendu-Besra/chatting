"""
app/websocket/connection_manager.py
------------------------------------
Manages all active WebSocket connections in memory.

Why a ConnectionManager?
  We need to track which clients (WebSockets) are connected to which
  chat rooms so we can broadcast messages efficiently.

Data structure:
  active_connections: dict[chat_id_str → list[WebSocket]]

This works for a single-server deployment. For multi-server scaling,
you would use Redis Pub/Sub to forward messages between servers.
"""

import asyncio
from collections import defaultdict

from fastapi import WebSocket

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """
    Thread-safe WebSocket connection pool.
    
    Key operations:
    - connect(chat_id, websocket)   → add to pool
    - disconnect(chat_id, websocket) → remove from pool
    - broadcast(chat_id, message)   → send to all in room
    - send_personal(websocket, msg) → send to single client
    """

    def __init__(self):
        # chat_id (str) → list of connected WebSockets
        self.active_connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, chat_id: str, websocket: WebSocket) -> None:
        """Accept the WebSocket and register it under the chat room."""
        await websocket.accept()
        self.active_connections[chat_id].append(websocket)
        logger.info(
            "WebSocket connected",
            chat_id=chat_id,
            total_in_room=len(self.active_connections[chat_id]),
        )

    def disconnect(self, chat_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket from the pool on disconnect."""
        connections = self.active_connections.get(chat_id, [])
        if websocket in connections:
            connections.remove(websocket)
        # Clean up empty rooms
        if not connections:
            self.active_connections.pop(chat_id, None)
        logger.info("WebSocket disconnected", chat_id=chat_id)

    async def broadcast(self, chat_id: str, message: dict) -> None:
        """
        Send a JSON message to every WebSocket in a chat room.
        If a send fails (client disconnected), we silently remove them.
        """
        connections = self.active_connections.get(chat_id, [])
        dead_sockets = []

        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                dead_sockets.append(websocket)

        # Clean up dead connections
        for ws in dead_sockets:
            self.disconnect(chat_id, ws)

    async def send_personal(self, websocket: WebSocket, message: dict) -> None:
        """Send a JSON message to a single WebSocket client."""
        try:
            await websocket.send_json(message)
        except Exception:
            logger.warning("Failed to send personal message")

    def get_connection_count(self, chat_id: str) -> int:
        """Return number of active connections in a room."""
        return len(self.active_connections.get(chat_id, []))


# ── Singleton instance ────────────────────────────────────────────────────────
# Shared across all requests in the same process
manager = ConnectionManager()
