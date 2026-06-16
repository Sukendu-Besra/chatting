"""
migrations/env.py
-----------------
Alembic environment configuration.

Alembic uses a SYNCHRONOUS SQLAlchemy connection for migrations
(even if the app itself uses async). This is normal and expected.
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ── Load our app's Base and models ─────────────────────────────────────────
# This ensures Alembic can detect all our models for autogenerate
from app.database import Base
import app.models  # noqa: F401 — import all models so they register with Base

# ── Alembic Config object ──────────────────────────────────────────────────
config = context.config

# ── Logging ────────────────────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.config.settings import settings

# ── Override DB URL from environment variable ─────────────────────────────
# This allows docker-compose to inject the URL without editing alembic.ini
sync_url = settings.SYNC_DATABASE_URL
if sync_url:
    config.set_main_option("sqlalchemy.url", sync_url)

# ── MetaData for autogenerate ──────────────────────────────────────────────
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Only the URL is needed — no actual DB connection is established.
    Useful for generating SQL scripts without a live DB.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    Establishes a real connection and applies migrations immediately.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # No pooling needed for migration scripts
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
