"""
app/routers/users.py
---------------------
User profile and presence endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.redis.redis_client import get_online_users
from app.schemas.user import UserOut, UserPublic, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get my profile",
)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return current_user


@router.patch(
    "/me",
    response_model=UserOut,
    summary="Update my profile",
)
async def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the username of the current user."""
    if data.username:
        current_user.username = data.username
    db.add(current_user)
    return current_user


@router.get(
    "/",
    response_model=list[UserPublic],
    summary="List all registered users",
)
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return a list of all users with public info only.
    Useful for showing who you can start a chat with.
    """
    result = await db.execute(
        select(User).where(User.id != current_user.id).order_by(User.username)
    )
    return list(result.scalars().all())


@router.get(
    "/online",
    summary="Get list of currently online user IDs",
)
async def get_online_users_list(
    _: User = Depends(get_current_user),
) -> dict:
    """
    Returns set of user IDs that are currently connected via WebSocket.
    Data comes from Redis for fast response.
    """
    online = await get_online_users()
    return {"online_users": list(online), "count": len(online)}


@router.get(
    "/{user_id}",
    response_model=UserPublic,
    summary="Get public profile of a user",
)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get public profile for any user by their UUID."""
    import uuid
    from fastapi import HTTPException, status

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
