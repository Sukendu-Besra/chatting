"""
app/routers/groups.py
----------------------
Group chat management: CRUD + member management.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.group import GroupAddMember, GroupCreate, GroupOut, GroupUpdate
from app.schemas.user import UserPublic
from app.services.chat_service import get_chat_members
from app.services.group_service import (
    add_member_to_group,
    create_group,
    get_group_or_404,
    get_user_groups,
    remove_member_from_group,
    require_group_admin,
)

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.post(
    "/",
    response_model=GroupOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new group chat",
)
async def create_new_group(
    data: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a group chat. The creator automatically becomes admin.
    Optionally pass `member_ids` to add users immediately.
    """
    return await create_group(data, current_user, db)


@router.get(
    "/",
    response_model=list[GroupOut],
    summary="List my groups",
)
async def list_my_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all groups the current user is a member of."""
    return await get_user_groups(current_user, db)


@router.get(
    "/{group_id}",
    response_model=GroupOut,
    summary="Get group details",
)
async def get_group(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_group_or_404(group_id, db)


@router.patch(
    "/{group_id}",
    response_model=GroupOut,
    summary="Update group name/description (admin only)",
)
async def update_group(
    group_id: uuid.UUID,
    data: GroupUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Only the group admin can update group metadata."""
    group = await get_group_or_404(group_id, db)
    await require_group_admin(group, current_user)

    if data.name is not None:
        group.name = data.name
    if data.description is not None:
        group.description = data.description

    db.add(group)
    return group


@router.post(
    "/{group_id}/members",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member to the group (admin only)",
)
async def add_member(
    group_id: uuid.UUID,
    data: GroupAddMember,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a user to the group. Only admin can do this."""
    group = await get_group_or_404(group_id, db)
    await require_group_admin(group, current_user)
    await add_member_to_group(group, data.user_id, db)
    return {"detail": "Member added successfully"}


@router.delete(
    "/{group_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from the group (admin only)",
)
async def remove_member(
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a user from the group. Only admin can do this."""
    group = await get_group_or_404(group_id, db)
    await require_group_admin(group, current_user)
    await remove_member_from_group(group, user_id, db)


@router.get(
    "/{group_id}/members",
    response_model=list[UserPublic],
    summary="List group members",
)
async def list_members(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all members of a group."""
    group = await get_group_or_404(group_id, db)
    return await get_chat_members(group.chat_id, db)
