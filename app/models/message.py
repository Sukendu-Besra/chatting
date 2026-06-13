"""
app/models/message.py
---------------------
Message table: stores all chat messages (private and group).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Delivery tracking
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # ── Relationships ────────────────────────────────────────────────────────
    sender: Mapped["User"] = relationship("User", back_populates="messages")  # noqa: F821
    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Message id={self.id} chat={self.chat_id} sender={self.sender_id}>"
