"""
app/models/__init__.py
----------------------
Import all models here so Alembic can discover them automatically.
"""

from app.models.user import User
from app.models.chat import Chat, ChatMember, ChatType
from app.models.message import Message
from app.models.group import Group

__all__ = ["User", "Chat", "ChatMember", "ChatType", "Message", "Group"]
