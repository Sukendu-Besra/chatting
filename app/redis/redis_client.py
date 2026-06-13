"""
app/redis/redis_client.py
--------------------------
Redis connection and presence tracking helpers.

Why Redis for presence?
  - Redis is in-memory, so reads/writes are ~microseconds vs milliseconds for DB.
  - Redis Sets are perfect for tracking a group of online users.
  - Redis Pub/Sub lets us broadcast typing events across multiple app servers
    (horizontal scaling).

Key design:
  SADD online_users <user_id>   → mark online
  SREM online_users <user_id>   → mark offline
  SMEMBERS online_users         → get all online users
  
  PUBLISH typing:<chat_id> <user_id>  → broadcast typing event
  SUBSCRIBE typing:<chat_id>          → receive typing events
"""

import redis.asyncio as aioredis

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Module-level client (singleton) ──────────────────────────────────────────
# Created once at startup, reused across all requests (connection pooling built-in)
redis_client: aioredis.Redis | None = None

ONLINE_USERS_KEY = "online_users"


async def get_redis() -> aioredis.Redis:
    """Return the module-level Redis client."""
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return redis_client


async def connect_redis() -> None:
    """Called on application startup to initialise the Redis client."""
    global redis_client
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
    )
    # Ping to verify connection
    await redis_client.ping()
    logger.info("Redis connected", url=settings.REDIS_URL)


async def disconnect_redis() -> None:
    """Called on application shutdown."""
    global redis_client
    if redis_client:
        await redis_client.aclose()
        redis_client = None
        logger.info("Redis disconnected")


# ── Presence Helpers ──────────────────────────────────────────────────────────

async def set_user_online(user_id: str) -> None:
    """Add user to the online set."""
    r = await get_redis()
    await r.sadd(ONLINE_USERS_KEY, user_id)
    logger.debug("User online", user_id=user_id)


async def set_user_offline(user_id: str) -> None:
    """Remove user from the online set."""
    r = await get_redis()
    await r.srem(ONLINE_USERS_KEY, user_id)
    logger.debug("User offline", user_id=user_id)


async def get_online_users() -> set[str]:
    """Return set of online user ID strings."""
    r = await get_redis()
    return await r.smembers(ONLINE_USERS_KEY)


async def is_user_online(user_id: str) -> bool:
    """Check if a specific user is online."""
    r = await get_redis()
    return bool(await r.sismember(ONLINE_USERS_KEY, user_id))


# ── Typing Indicator via Pub/Sub ──────────────────────────────────────────────

async def publish_typing(chat_id: str, user_id: str, is_typing: bool) -> None:
    """
    Publish a typing event to a Redis channel.
    All app instances subscribed to this channel will forward it to their WebSocket clients.
    """
    r = await get_redis()
    channel = f"typing:{chat_id}"
    payload = f"{user_id}:{'1' if is_typing else '0'}"
    await r.publish(channel, payload)
