"""
app/schemas/user.py
-------------------
Pydantic schemas for User request/response validation.

Pydantic automatically validates incoming JSON and converts types.
Having separate Input/Output schemas prevents over-posting attacks
(e.g., a user sending hashed_password in a request body).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Input Schemas (Request) ───────────────────────────────────────────────────

class UserRegister(BaseModel):
    """Used for POST /auth/register"""
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def username_lowercase(cls, v: str) -> str:
        return v.lower()


class UserLogin(BaseModel):
    """Used for POST /auth/login"""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Used for PATCH /users/me"""
    username: str | None = Field(None, min_length=3, max_length=50)


# ── Output Schemas (Response) ─────────────────────────────────────────────────

class UserOut(BaseModel):
    """Safe public representation of a user — never exposes hashed_password."""
    id: uuid.UUID
    username: str
    email: str
    is_active: bool
    created_at: datetime
    last_seen: datetime

    model_config = {"from_attributes": True}  # enables ORM mode


class UserPublic(BaseModel):
    """Minimal user info for listing in chats."""
    id: uuid.UUID
    username: str
    is_active: bool
    last_seen: datetime

    model_config = {"from_attributes": True}
