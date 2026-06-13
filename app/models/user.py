"""
app/models/user.py
------------------
User table definition.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


    # ── Relationships ────────────────────────────────────────────────────────
    # Messages sent by this user
    messages: Mapped[list["Message"]] = relationship(  # noqa: F821
        "Message", back_populates="sender", lazy="noload"
    )
    # Chat rooms this user is a member of
    chat_memberships: Mapped[list["ChatMember"]] = relationship(  # noqa: F821
        "ChatMember", back_populates="user", lazy="noload"
    )
    # Groups where this user is admin
    admin_groups: Mapped[list["Group"]] = relationship(  # noqa: F821
        "Group", back_populates="admin", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username}>"
