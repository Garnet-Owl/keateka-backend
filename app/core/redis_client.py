import json
from typing import Any, Optional
import redis as redis_pkg  # Renamed import to avoid conflict
from app.core.config import settings

# Create Redis connection pool
redis_client = redis_pkg.from_url(
    settings.REDIS_URL, encoding="utf-8", decode_responses=True
)


def set_key(key: str, value: Any, expire: Optional[int] = None) -> bool:
    """
    Set a key in Redis with optional expiration
    """
    try:
        redis_client.set(key, json.dumps(value))
        if expire:
            redis_client.expire(key, expire)
        return True
    except Exception as e:
        print(f"Redis set error: {e}")
        return False


def get_key(key: str) -> Optional[Any]:
    """
    Get a key from Redis
    """
    try:
        value = redis_client.get(key)
        return json.loads(value) if value else None
    except Exception as e:
        print(f"Redis get error: {e}")
        return None


def delete_key(key: str) -> bool:
    """
    Delete a key from Redis
    """
    try:
        return bool(redis_client.delete(key))
    except Exception as e:
        print(f"Redis delete error: {e}")
        return False


def clear_pattern(pattern: str) -> bool:
    """
    Clear all keys matching a pattern
    """
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
        return True
    except Exception as e:
        print(f"Redis clear pattern error: {e}")
        return False
