"""
app/models/group.py
-------------------
Group table: metadata for group chats.
Each Group is linked 1-to-1 with a Chat of type 'group'.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Foreign keys
    admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ────────────────────────────────────────────────────────
    admin: Mapped["User"] = relationship("User", back_populates="admin_groups")  # noqa: F821
    chat: Mapped["Chat"] = relationship("Chat", back_populates="group")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Group id={self.id} name={self.name}>"
