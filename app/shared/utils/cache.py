from datetime import timedelta
from functools import wraps
import logging
import pickle
from typing import Any, Callable, Optional, Union

from redis import Redis

logger = logging.getLogger(__name__)


class CacheManager:
    """Cache manager for Redis backend."""

    def __init__(self, redis_client: Redis, prefix: str = "cache") -> None:
        self.redis = redis_client
        self.prefix = prefix

    def _get_key(self, key: str) -> str:
        """Generate prefixed cache key."""
        return f"{self.prefix}:{key}"

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache.

        Args:
            key: Cache key
            default: Default value if key not found
        """
        try:
            value = self.redis.get(self._get_key(key))
            if value is None:
                return default
            return pickle.loads(value)
        except Exception as e:
            logger.exception(f"Error retrieving from cache: {e!s}")
            return default

    async def set(
        self,
        key: str,
        value: Any,
        expires_in: Optional[Union[int, timedelta]] = None,
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            expires_in: Expiration time in seconds or timedelta
        """
        try:
            serialized = pickle.dumps(value)
            if isinstance(expires_in, timedelta):
                expires_in = int(expires_in.total_seconds())

            return bool(
                self.redis.set(self._get_key(key), serialized, ex=expires_in)
            )
        except Exception as e:
            logger.exception(f"Error setting cache: {e!s}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            return bool(self.redis.delete(self._get_key(key)))
        except Exception as e:
            logger.exception(f"Error deleting from cache: {e!s}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return bool(self.redis.exists(self._get_key(key)))
        except Exception as e:
            logger.exception(f"Error checking cache existence: {e!s}")
            return False

    async def delete_pattern(self, pattern: str) -> bool:
        """Delete keys matching pattern."""
        try:
            keys = self.redis.keys(self._get_key(pattern))
            if keys:
                return bool(self.redis.delete(*keys))
            return True
        except Exception as e:
            logger.exception(f"Error deleting pattern from cache: {e!s}")
            return False


def cached(
    expire: Optional[Union[int, timedelta]] = None,
    key_prefix: str = "cache",
    key_builder: Optional[Callable[..., str]] = None,
):
    """
    Decorator for caching function results.

    Args:
        expire: Cache expiration time
        key_prefix: Prefix for cache keys
        key_builder: Custom function to build cache key

    Usage:
        @cached(expire=300)
        async def get_user_data(user_id: int):
            return await db.fetch_user(user_id)
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get Redis client from first arg (self) if available
            redis_client = getattr(args[0], "redis", None) if args else None
            if not redis_client:
                raise ValueError("Redis client not available")

            cache = CacheManager(redis_client, key_prefix)

            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key builder using function name and arguments
                arg_str = ":".join(str(arg) for arg in args[1:])  # Skip self
                kwarg_str = ":".join(f"{k}={v}" for k, v in kwargs.items())
                cache_key = f"{func.__name__}:{arg_str}:{kwarg_str}"

            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # If not in cache, execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, expires_in=expire)
            return result

        return wrapper

    return decorator


# Cache invalidation decorator
def invalidate_cache(
    key_pattern: str,
    key_prefix: str = "cache",
):
    """
    Decorator for invalidating cache entries matching a pattern.

    Args:
        key_pattern: Pattern to match cache keys
        key_prefix: Prefix for cache keys

    Usage:
        @invalidate_cache("user:*")
        async def update_user(user_id: int, data: dict):
            return await db.update_user(user_id, data)
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get Redis client from first arg (self) if available
            redis_client = getattr(args[0], "redis", None) if args else None
            if not redis_client:
                raise ValueError("Redis client not available")

            cache = CacheManager(redis_client, key_prefix)

            # Execute function first
            result = await func(*args, **kwargs)

            # Delete matching cache keys
            pattern = cache._get_key(key_pattern)
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)

            return result

        return wrapper

    return decorator


async def get_redis_client() -> Redis:
    """Dependency to get Redis client."""
    from app.shared.config import settings

    return Redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=settings.REDIS_POOL_SIZE,
    )
