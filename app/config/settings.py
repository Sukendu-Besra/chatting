"""
app/config/settings.py
----------------------
Centralised settings loaded from environment variables.
Uses Pydantic-Settings which automatically reads .env files.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # ── Application ────────────────────────────────────────────────────────
    APP_NAME: str = "ChatApp"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Security / JWT ─────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Database ───────────────────────────────────────────────────────────
    # Async URL used by SQLAlchemy async engine (asyncpg driver)
    DATABASE_URL: str = "postgresql+asyncpg://chatuser:chatpassword@db:5432/chatdb"
    # Sync URL used only by Alembic migrations
    SYNC_DATABASE_URL: str = "postgresql://chatuser:chatpassword@db:5432/chatdb"

    # ── Redis ──────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    # Tell Pydantic-Settings where to find the .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Return a cached Settings instance.
    lru_cache ensures we only read .env once per process.
    """
    return Settings()


# Convenient module-level alias so other modules can do:
#   from app.config.settings import settings
settings = get_settings()
