"""
app/websocket/ws_router.py
---------------------------
WebSocket endpoint for real-time chat.

Connection URL: ws://host/ws/{chat_id}?token=<jwt_access_token>

Message Protocol (JSON):
  Client → Server:
    { "type": "message", "content": "Hello!" }
    { "type": "typing",  "is_typing": true }
    { "type": "ping" }

  Server → Client (broadcast):
    { "type": "message",   "content": "...", "sender_id": "...", "sender": "...", "chat_id": "...", "timestamp": "..." }
    { "type": "typing",    "user_id": "...", "username": "...", "is_typing": true }
    { "type": "user_joined", "user_id": "...", "username": "..." }
    { "type": "user_left",   "user_id": "...", "username": "..." }
    { "type": "online_users", "users": [...] }
    { "type": "error",     "detail": "..." }
    { "type": "pong" }
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user_ws
from app.database import get_db
from app.models.user import User
from app.redis.redis_client import (
    get_online_users,
    publish_typing,
    set_user_offline,
    set_user_online,
)
from app.services.chat_service import verify_chat_membership
from app.services.message_service import save_message
from app.websocket.connection_manager import manager
from app.utils.logger import get_logger

logger = get_logger(__name__)

ws_router = APIRouter()


@ws_router.websocket("/ws/{chat_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    chat_id: uuid.UUID,
    current_user: User = Depends(get_current_user_ws),
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for real-time chat.

    Lifecycle:
    1. Accept connection
    2. Verify user is a chat member
    3. Mark user online in Redis
    4. Broadcast "user_joined" to room
    5. Listen for messages in a loop
    6. On disconnect: mark offline, broadcast "user_left"
    """
    chat_id_str = str(chat_id)
    user_id_str = str(current_user.id)

    # ── Step 1: Verify membership before accepting ────────────────────────────
    try:
        await verify_chat_membership(current_user.id, chat_id, db)
    except Exception:
        await websocket.close(code=4003, reason="Not a member of this chat")
        return

    # ── Step 2: Connect ───────────────────────────────────────────────────────
    await manager.connect(chat_id_str, websocket)
    await set_user_online(user_id_str)

    # ── Step 3: Notify room that user joined ──────────────────────────────────
    online_users = await get_online_users()
    await manager.broadcast(chat_id_str, {
        "type": "user_joined",
        "user_id": user_id_str,
        "username": current_user.username,
        "online_users": list(online_users),
    })

    try:
        # ── Step 4: Message loop ──────────────────────────────────────────────
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "message")

            # ── Ping / Keepalive ──────────────────────────────────────────────
            if msg_type == "ping":
                await manager.send_personal(websocket, {"type": "pong"})
                continue

            # ── Typing Indicator ──────────────────────────────────────────────
            if msg_type == "typing":
                is_typing = data.get("is_typing", False)
                # Publish to Redis so all servers receive it
                await publish_typing(chat_id_str, user_id_str, is_typing)
                # Also broadcast locally
                await manager.broadcast(chat_id_str, {
                    "type": "typing",
                    "user_id": user_id_str,
                    "username": current_user.username,
                    "is_typing": is_typing,
                })
                continue

            # ── Chat Message ──────────────────────────────────────────────────
            if msg_type == "message":
                content = data.get("content", "").strip()
                if not content:
                    await manager.send_personal(websocket, {
                        "type": "error",
                        "detail": "Message content cannot be empty",
                    })
                    continue

                if len(content) > 4000:
                    await manager.send_personal(websocket, {
                        "type": "error",
                        "detail": "Message too long (max 4000 characters)",
                    })
                    continue

                # Persist to PostgreSQL
                message = await save_message(
                    sender_id=current_user.id,
                    chat_id=chat_id,
                    content=content,
                    db=db,
                )
                await db.commit()

                # Broadcast to all members in the room
                await manager.broadcast(chat_id_str, {
                    "type": "message",
                    "id": str(message.id),
                    "sender_id": user_id_str,
                    "sender": current_user.username,
                    "chat_id": chat_id_str,
                    "content": content,
                    "timestamp": message.created_at.isoformat(),
                })
                continue

            # Unknown message type
            await manager.send_personal(websocket, {
                "type": "error",
                "detail": f"Unknown message type: {msg_type}",
            })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", user=current_user.username, chat=chat_id_str)

    except Exception as e:
        logger.error("WebSocket error", error=str(e), user=current_user.username)

    finally:
        # ── Step 5: Cleanup on disconnect ─────────────────────────────────────
        manager.disconnect(chat_id_str, websocket)
        await set_user_offline(user_id_str)

        # Update last_seen in DB
        from sqlalchemy import update
        from datetime import datetime, timezone
        await db.execute(
            update(User)
            .where(User.id == current_user.id)
            .values(last_seen=datetime.now(timezone.utc))
        )
        await db.commit()

        # Notify remaining users
        online_users = await get_online_users()
        await manager.broadcast(chat_id_str, {
            "type": "user_left",
            "user_id": user_id_str,
            "username": current_user.username,
            "online_users": list(online_users),
        })
