"""
app/auth/dependencies.py
------------------------
FastAPI dependency for extracting and validating the current user
from the Authorization header on every protected route.

Usage:
    @router.get("/protected")
    async def protected_route(current_user: User = Depends(get_current_user)):
        ...
"""

import uuid

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.jwt_handler import decode_token
from app.database import get_db
from app.models.user import User

# Tells FastAPI where the token comes from (used in Swagger UI)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract user from JWT access token sent in Authorization header.
    
    1. Parse Bearer token
    2. Decode JWT → get user_id
    3. Query DB for user
    4. Return user or raise 401
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user_id_str = decode_token(token, expected_type="access")
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


async def get_current_user_ws(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    WebSocket variant of get_current_user.
    Token is passed as a query parameter: /ws/{chat_id}?token=<jwt>
    
    WebSockets don't support HTTP headers for the initial handshake,
    so we use a query param for authentication instead.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate WebSocket credentials",
    )

    try:
        user_id_str = decode_token(token, expected_type="access")
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception

    return user
