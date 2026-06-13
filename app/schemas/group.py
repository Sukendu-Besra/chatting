"""
app/schemas/group.py
--------------------
Pydantic schemas for Group chat management.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = Field(None, max_length=500)
    member_ids: list[uuid.UUID] = Field(default_factory=list)


class GroupUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = Field(None, max_length=500)


class GroupAddMember(BaseModel):
    user_id: uuid.UUID


class GroupOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    admin_id: uuid.UUID | None
    chat_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Auth Schemas ──────────────────────────────────────────────────────────────
# Kept here for simplicity; commonly placed in a dedicated auth schema file

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str
