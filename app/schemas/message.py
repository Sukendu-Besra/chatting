"""
app/schemas/message.py
----------------------
Pydantic schemas for Messages.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """Body for sending a message via REST (WebSocket uses raw JSON)."""
    content: str = Field(..., min_length=1, max_length=4000)


class MessageOut(BaseModel):
    id: uuid.UUID
    sender_id: uuid.UUID | None
    chat_id: uuid.UUID
    content: str
    is_read: bool
    delivered: bool
    created_at: datetime

    # Optional: embed sender username for convenience
    sender_username: str | None = None

    model_config = {"from_attributes": True}


class PaginatedMessages(BaseModel):
    """Paginated message list response."""
    messages: list[MessageOut]
    total: int
    page: int
    limit: int
    has_next: bool
