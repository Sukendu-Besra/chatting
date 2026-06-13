"""
app/services/chat_service.py
-----------------------------
Business logic for creating and retrieving chats.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import Chat, ChatMember, ChatType
from app.models.user import User
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def get_or_create_private_chat(
    current_user: User, other_user_id: uuid.UUID, db: AsyncSession
) -> Chat:
    """
    Find an existing 1-to-1 chat between two users, or create one.
    
    We find existing chats by looking for a chat where both users
    are members and the type is 'private'.
    """
    if current_user.id == other_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create a chat with yourself",
        )

    # Verify other user exists
    result = await db.execute(select(User).where(User.id == other_user_id))
    other_user = result.scalar_one_or_none()
    if not other_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Look for existing private chat shared between both users
    # Subquery: chat IDs where current user is a member
    my_chats = select(ChatMember.chat_id).where(ChatMember.user_id == current_user.id)
    # Subquery: chat IDs where other user is a member
    their_chats = select(ChatMember.chat_id).where(ChatMember.user_id == other_user_id)

    result = await db.execute(
        select(Chat).where(
            and_(
                Chat.type == ChatType.private,
                Chat.id.in_(my_chats),
                Chat.id.in_(their_chats),
            )
        )
    )
    existing_chat = result.scalar_one_or_none()

    if existing_chat:
        return existing_chat

    # Create new private chat
    chat = Chat(type=ChatType.private)
    db.add(chat)
    await db.flush()

    # Add both users as members
    db.add(ChatMember(user_id=current_user.id, chat_id=chat.id))
    db.add(ChatMember(user_id=other_user_id, chat_id=chat.id))
    await db.flush()

    logger.info(
        "Private chat created",
        chat_id=str(chat.id),
        user1=str(current_user.id),
        user2=str(other_user_id),
    )
    return chat


async def get_user_chats(user: User, db: AsyncSession) -> list[Chat]:
    """Return all chats a user is a member of."""
    result = await db.execute(
        select(Chat)
        .join(ChatMember, Chat.id == ChatMember.chat_id)
        .where(ChatMember.user_id == user.id)
        .order_by(Chat.created_at.desc())
    )
    return list(result.scalars().all())


async def verify_chat_membership(
    user_id: uuid.UUID, chat_id: uuid.UUID, db: AsyncSession
) -> Chat:
    """
    Verify that a user belongs to a chat. Used by WebSocket and message endpoints.
    Raises 403 if user is not a member.
    """
    result = await db.execute(
        select(Chat)
        .join(ChatMember, Chat.id == ChatMember.chat_id)
        .where(and_(Chat.id == chat_id, ChatMember.user_id == user_id))
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this chat",
        )
    return chat


async def get_chat_members(chat_id: uuid.UUID, db: AsyncSession) -> list[User]:
    """Return all users in a chat."""
    result = await db.execute(
        select(User)
        .join(ChatMember, User.id == ChatMember.user_id)
        .where(ChatMember.chat_id == chat_id)
    )
    return list(result.scalars().all())
