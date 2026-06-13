"""
app/routers/chats.py
---------------------
Chat management and message history endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.chat import ChatCreate, ChatOut
from app.schemas.message import PaginatedMessages
from app.schemas.user import UserPublic
from app.services.chat_service import (
    get_chat_members,
    get_or_create_private_chat,
    get_user_chats,
    verify_chat_membership,
)
from app.services.message_service import get_message_history, mark_messages_read

router = APIRouter(prefix="/chats", tags=["Chats"])


@router.post(
    "/",
    response_model=ChatOut,
    summary="Get or create a private chat with another user",
)
async def get_or_create_chat(
    data: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Idempotent: if a private chat already exists between the two users,
    it returns the existing chat instead of creating a new one.
    """
    chat = await get_or_create_private_chat(current_user, data.other_user_id, db)
    return chat


@router.get(
    "/",
    response_model=list[ChatOut],
    summary="List all my chats",
)
async def list_my_chats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all chat rooms (private + group) the current user is a member of."""
    return await get_user_chats(current_user, db)


@router.get(
    "/{chat_id}/messages",
    response_model=PaginatedMessages,
    summary="Get paginated message history for a chat",
)
async def get_chat_messages(
    chat_id: uuid.UUID,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(default=50, ge=1, le=100, description="Messages per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch message history with pagination.
    
    - Ordered oldest → newest
    - Use page/limit to paginate
    - Also marks messages as read for this user
    """
    # Verify membership
    await verify_chat_membership(current_user.id, chat_id, db)

    # Mark messages as read
    await mark_messages_read(chat_id, current_user.id, db)

    # Fetch paginated history
    return await get_message_history(chat_id, page, limit, db)


@router.get(
    "/{chat_id}/members",
    response_model=list[UserPublic],
    summary="Get members of a chat",
)
async def get_members(
    chat_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all users who are members of a specific chat."""
    await verify_chat_membership(current_user.id, chat_id, db)
    return await get_chat_members(chat_id, db)
