"""
app/auth/jwt_handler.py
-----------------------
JWT (JSON Web Token) creation and verification.

JWT Flow:
1. User logs in → server issues access_token + refresh_token
2. Client stores tokens (localStorage / cookie)
3. Client sends: Authorization: Bearer <access_token>
4. Server validates signature using SECRET_KEY
5. If access_token expires → client uses refresh_token to get new access_token

Why two tokens?
  - access_token: Short-lived (30 min). Used for every API request.
  - refresh_token: Long-lived (7 days). Stored securely, used only to refresh.
  This limits damage if access_token is stolen.
"""

from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import JWTError, jwt

from app.config.settings import settings


def _create_token(
    subject: str,
    token_type: Literal["access", "refresh"],
    expires_delta: timedelta,
) -> str:
    """
    Internal helper to build a signed JWT.

    Payload fields:
      sub  — subject (user ID as string)
      type — "access" or "refresh" (prevents token confusion attacks)
      exp  — expiry timestamp
      iat  — issued-at timestamp
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: str) -> str:
    """Create a short-lived access token."""
    return _create_token(
        subject=user_id,
        token_type="access",
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived refresh token."""
    return _create_token(
        subject=user_id,
        token_type="refresh",
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, expected_type: Literal["access", "refresh"] = "access") -> str:
    """
    Decode and validate a JWT token.

    Returns the user_id (subject) string on success.
    Raises JWTError on invalid/expired tokens.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")

        if user_id is None:
            raise JWTError("Token missing subject")

        if token_type != expected_type:
            raise JWTError(f"Expected {expected_type} token, got {token_type}")

        return user_id

    except JWTError:
        raise  # Let the caller handle it
