"""
app/services/auth_service.py
-----------------------------
Business logic for user registration and login.

The service layer sits between routers (HTTP layer) and models (DB layer).
This separation makes the code testable and reusable.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.user import UserRegister
from app.schemas.group import Token
from app.auth.password import hash_password, verify_password
from app.auth.jwt_handler import create_access_token, create_refresh_token
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def register_user(data: UserRegister, db: AsyncSession) -> User:
    """
    Register a new user.
    
    Steps:
    1. Check email/username uniqueness
    2. Hash password
    3. Persist to DB
    """
    # Check for duplicate email
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Check for duplicate username
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.flush()  # Flush to get the generated UUID without committing
    await db.refresh(user)

    logger.info("New user registered", username=user.username, user_id=str(user.id))
    return user


async def login_user(email: str, password: str, db: AsyncSession) -> Token:
    """
    Authenticate a user and issue JWT tokens.
    
    Steps:
    1. Find user by email
    2. Verify password
    3. Issue access + refresh tokens
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Use same error for both "not found" and "wrong password"
    # (prevents user enumeration attacks)
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    user_id = str(user.id)
    logger.info("User logged in", username=user.username)

    return Token(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )
