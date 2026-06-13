"""
app/database.py
---------------
SQLAlchemy async engine and session factory.

Why async?
  FastAPI is built on asyncio. Using async SQLAlchemy means our DB calls
  are non-blocking — the event loop can handle other requests while waiting
  for the database, giving us much better throughput under load.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import settings


# ── Async Engine ──────────────────────────────────────────────────────────────
# pool_pre_ping=True — validate connections before use (handles DB restarts)
# echo=False        — set True locally to see SQL in logs
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    pool_size=10,           # Number of persistent connections in pool
    max_overflow=20,        # Extra connections allowed beyond pool_size
)

# ── Session Factory ───────────────────────────────────────────────────────────
# expire_on_commit=False — keep ORM objects usable after commit
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Declarative Base ──────────────────────────────────────────────────────────
# All SQLAlchemy models inherit from this Base
class Base(DeclarativeBase):
    pass


# ── Dependency ────────────────────────────────────────────────────────────────
async def get_db() -> AsyncSession:
    """
    FastAPI dependency that yields a database session per request.
    The session is automatically closed when the request ends.

    Usage in a router:
        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
