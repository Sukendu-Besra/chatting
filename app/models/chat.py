"""
app/models/chat.py
------------------
Chat room and membership tables.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
import enum


class ChatType(str, enum.Enum):
    private = "private"
    group = "group"


class Chat(Base):
    """
    A Chat is a logical room that can hold messages.
    It can be a 1-to-1 (private) or group conversation.
    """
    __tablename__ = "chats"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    type: Mapped[ChatType] = mapped_column(
        Enum(ChatType), nullable=False, default=ChatType.private
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ────────────────────────────────────────────────────────
    members: Mapped[list["ChatMember"]] = relationship(
        "ChatMember", back_populates="chat", lazy="noload"
    )
    messages: Mapped[list["Message"]] = relationship(  # noqa: F821
        "Message", back_populates="chat", lazy="noload"
    )
    group: Mapped["Group"] = relationship(  # noqa: F821
        "Group", back_populates="chat", uselist=False, lazy="noload"
    )


class ChatMember(Base):
    """
    Join table between Users and Chats.
    Tracks which users belong to which chat rooms.
    """
    __tablename__ = "chat_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="chat_memberships")  # noqa: F821
    chat: Mapped["Chat"] = relationship("Chat", back_populates="members")

    def __repr__(self) -> str:
        return f"<ChatMember user={self.user_id} chat={self.chat_id}>"
