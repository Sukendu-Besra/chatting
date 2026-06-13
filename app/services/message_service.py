"""
app/services/message_service.py
---------------------------------
Persist messages to DB and retrieve message history with pagination.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.message import Message
from app.models.user import User
from app.schemas.message import MessageOut, PaginatedMessages
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def save_message(
    sender_id: uuid.UUID,
    chat_id: uuid.UUID,
    content: str,
    db: AsyncSession,
) -> Message:
    """
    Persist a chat message to PostgreSQL.
    Called by the WebSocket handler after broadcasting.
    """
    message = Message(
        sender_id=sender_id,
        chat_id=chat_id,
        content=content,
        delivered=True,  # Mark as delivered since it was sent over WS
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    return message


async def get_message_history(
    chat_id: uuid.UUID,
    page: int,
    limit: int,
    db: AsyncSession,
) -> PaginatedMessages:
    """
    Fetch paginated message history for a chat.
    
    Pagination uses OFFSET/LIMIT — good enough for moderate scale.
    For millions of messages, use cursor-based pagination (created_at < cursor).
    """
    offset = (page - 1) * limit

    # Count total messages in this chat
    count_result = await db.execute(
        select(func.count()).where(Message.chat_id == chat_id)
    )
    total = count_result.scalar_one()

    # Fetch the page of messages with sender join
    result = await db.execute(
        select(Message, User.username.label("sender_username"))
        .join(User, Message.sender_id == User.id, isouter=True)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    rows = result.all()

    messages_out = []
    for message, sender_username in rows:
        msg_dict = {
            "id": message.id,
            "sender_id": message.sender_id,
            "chat_id": message.chat_id,
            "content": message.content,
            "is_read": message.is_read,
            "delivered": message.delivered,
            "created_at": message.created_at,
            "sender_username": sender_username,
        }
        messages_out.append(MessageOut(**msg_dict))

    return PaginatedMessages(
        messages=messages_out,
        total=total,
        page=page,
        limit=limit,
        has_next=(offset + limit) < total,
    )


async def mark_messages_read(
    chat_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> int:
    """
    Mark all unread messages in a chat as read for a specific user.
    Returns the number of messages marked.
    """
    from sqlalchemy import update
    result = await db.execute(
        update(Message)
        .where(
            Message.chat_id == chat_id,
            Message.sender_id != user_id,
            Message.is_read == False,  # noqa: E712
        )
        .values(is_read=True)
    )
    return result.rowcount
