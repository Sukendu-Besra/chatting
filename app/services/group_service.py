"""
app/services/group_service.py
------------------------------
Business logic for group chat management.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Chat, ChatMember, ChatType
from app.models.group import Group
from app.models.user import User
from app.schemas.group import GroupCreate, GroupUpdate
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def create_group(
    data: GroupCreate, admin: User, db: AsyncSession
) -> Group:
    """
    Create a new group chat.

    Steps:
    1. Create a Chat of type 'group'
    2. Create the Group record linking to that Chat
    3. Add admin + requested members as ChatMembers
    """
    # Create the underlying chat room
    chat = Chat(type=ChatType.group)
    db.add(chat)
    await db.flush()

    # Create the group metadata
    group = Group(
        name=data.name,
        description=data.description,
        admin_id=admin.id,
        chat_id=chat.id,
    )
    db.add(group)
    await db.flush()

    # Add admin as first member
    member_ids = {admin.id}
    db.add(ChatMember(user_id=admin.id, chat_id=chat.id))

    # Add requested members (skip duplicates)
    for uid in data.member_ids:
        if uid not in member_ids:
            result = await db.execute(select(User).where(User.id == uid))
            if result.scalar_one_or_none():
                db.add(ChatMember(user_id=uid, chat_id=chat.id))
                member_ids.add(uid)

    await db.flush()
    await db.refresh(group)

    logger.info("Group created", group_id=str(group.id), admin=str(admin.id))
    return group


async def get_group_or_404(group_id: uuid.UUID, db: AsyncSession) -> Group:
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return group


async def require_group_admin(group: Group, user: User) -> None:
    """Raise 403 if user is not the group admin."""
    if group.admin_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the group admin can perform this action",
        )


async def add_member_to_group(
    group: Group, user_id: uuid.UUID, db: AsyncSession
) -> ChatMember:
    """Add a user to a group's chat. Idempotent."""
    # Check user exists
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check not already a member
    result = await db.execute(
        select(ChatMember).where(
            and_(ChatMember.chat_id == group.chat_id, ChatMember.user_id == user_id)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this group",
        )

    member = ChatMember(user_id=user_id, chat_id=group.chat_id)
    db.add(member)
    await db.flush()
    return member


async def remove_member_from_group(
    group: Group, user_id: uuid.UUID, db: AsyncSession
) -> None:
    """Remove a user from a group. Admin cannot remove themselves."""
    if user_id == group.admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin cannot remove themselves from the group",
        )

    result = await db.execute(
        select(ChatMember).where(
            and_(ChatMember.chat_id == group.chat_id, ChatMember.user_id == user_id)
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this group",
        )

    await db.delete(member)


async def get_user_groups(user: User, db: AsyncSession) -> list[Group]:
    """Get all groups a user belongs to."""
    result = await db.execute(
        select(Group)
        .join(Chat, Group.chat_id == Chat.id)
        .join(ChatMember, Chat.id == ChatMember.chat_id)
        .where(ChatMember.user_id == user.id)
        .order_by(Group.created_at.desc())
    )
    return list(result.scalars().all())
