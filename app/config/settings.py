"""
app/config/settings.py
----------------------
Centralised settings loaded from environment variables.
Uses Pydantic-Settings which automatically reads .env files.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
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

    @model_validator(mode="before")
    @classmethod
    def assemble_settings(cls, data: dict) -> dict:
        # 1. Resolve Database URLs
        database_url = data.get("DATABASE_URL") or os.getenv("DATABASE_URL")
        sync_database_url = data.get("SYNC_DATABASE_URL") or os.getenv("SYNC_DATABASE_URL")

        if database_url:
            # If the database URL uses sync postgres scheme, change to asyncpg for DATABASE_URL
            if database_url.startswith("postgresql://"):
                data["DATABASE_URL"] = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
                # Fallback sync URL to the original sync database_url
                if not sync_database_url:
                    data["SYNC_DATABASE_URL"] = database_url
            elif database_url.startswith("postgresql+asyncpg://"):
                data["DATABASE_URL"] = database_url
                # Fallback sync URL to sync scheme
                if not sync_database_url:
                    data["SYNC_DATABASE_URL"] = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        elif sync_database_url:
            # If only sync URL is provided
            data["SYNC_DATABASE_URL"] = sync_database_url
            if sync_database_url.startswith("postgresql://"):
                data["DATABASE_URL"] = sync_database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        # 2. Resolve Redis URL
        redis_url = data.get("REDIS_URL") or os.getenv("REDIS_URL")
        if not redis_url:
            # Check other environment variables / alternative names
            resolved = False
            for alt_key in ["REDISPRIVATE_URL", "REDIS_PRIVATE_URL", "REDISURL"]:
                val = data.get(alt_key) or os.getenv(alt_key)
                if val:
                    data["REDIS_URL"] = val
                    resolved = True
                    break
            
            if not resolved:
                # Check if host/password details are defined separately
                host = data.get("REDISHOST") or os.getenv("REDISHOST")
                if host:
                    port = data.get("REDISPORT") or os.getenv("REDISPORT") or "6379"
                    password = data.get("REDISPASSWORD") or os.getenv("REDISPASSWORD")
                    user = data.get("REDISUSER") or os.getenv("REDISUSER") or "default"
                    if password:
                        data["REDIS_URL"] = f"redis://{user}:{password}@{host}:{port}/0"
                    else:
                        data["REDIS_URL"] = f"redis://{host}:{port}/0"
        else:
            data["REDIS_URL"] = redis_url

        return data

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
