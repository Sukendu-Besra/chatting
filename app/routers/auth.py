"""
app/routers/auth.py
--------------------
Authentication endpoints: register, login, refresh token.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.group import RefreshTokenRequest, Token
from app.schemas.user import UserLogin, UserOut, UserRegister
from app.services.auth_service import login_user, register_user
from app.auth.jwt_handler import create_access_token, decode_token, create_refresh_token
from jose import JWTError

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    data: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user.
    
    - Validates username uniqueness and email format
    - Hashes password using bcrypt
    - Returns the created user profile (no password)
    """
    user = await register_user(data, db)
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Login and receive JWT tokens",
)
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and return:
    - `access_token`: use in Authorization: Bearer header (expires in 30 min)
    - `refresh_token`: use to get new access token (expires in 7 days)
    """
    return await login_user(data.email, data.password, db)


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token using refresh token",
)
async def refresh_token(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange a valid refresh_token for a new access_token + refresh_token pair.
    
    Use this when the access_token expires (HTTP 401) to get a new one
    without requiring the user to log in again.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )
    try:
        user_id_str = decode_token(body.refresh_token, expected_type="refresh")
    except JWTError:
        raise credentials_exception

    return Token(
        access_token=create_access_token(user_id_str),
        refresh_token=create_refresh_token(user_id_str),
    )
