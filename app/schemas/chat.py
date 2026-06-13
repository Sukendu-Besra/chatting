"""
app/schemas/chat.py
-------------------
Pydantic schemas for Chat and ChatMember.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.chat import ChatType


class ChatCreate(BaseModel):
    """Create a private 1-to-1 chat by specifying the other user's ID."""
    other_user_id: uuid.UUID


class ChatOut(BaseModel):
    id: uuid.UUID
    type: ChatType
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMemberOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    chat_id: uuid.UUID
    joined_at: datetime

    model_config = {"from_attributes": True}
