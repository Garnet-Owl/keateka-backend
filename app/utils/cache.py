import json
from functools import wraps
from typing import Any, Callable

from fastapi import Request

from app.core.redis_client import redis_client


def generate_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """
    Generate a cache key based on function arguments
    """
    key_parts = [prefix]

    # Add positional arguments to key
    if args:
        key_parts.extend([str(arg) for arg in args])

    # Add keyword arguments to key
    if kwargs:
        sorted_items = sorted(kwargs.items())
        key_parts.extend([f"{k}:{v}" for k, v in sorted_items])

    return ":".join(key_parts)


def serialize_response(response: Any) -> str:
    """
    Serialize response data to string
    """
    if hasattr(response, "dict"):
        # Handle Pydantic models
        return json.dumps(response.dict())
    elif isinstance(response, (dict, list, str, int, float, bool)):
        # Handle basic types
        return json.dumps(response)
    else:
        # Try default serialization
        return json.dumps(response)


def deserialize_response(data: str) -> Any:
    """
    Deserialize cached data
    """
    return json.loads(data)


def cache_response(prefix: str, expire: int = 300):
    """
    Cache decorator for API responses

    Args:
        prefix: Prefix for cache key
        expire: Cache expiration time in seconds (default: 5 minutes)
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any):
            # Skip caching for non-GET requests
            request = next(
                (arg for arg in args if isinstance(arg, Request)), None
            )
            if request and request.method != "GET":
                return await func(*args, **kwargs)

            # Generate cache key
            cache_key = generate_cache_key(prefix, *args, **kwargs)

            # Try to get from cache
            cached_data = redis_client.get(cache_key)
            if cached_data:
                return deserialize_response(cached_data)

            # Get fresh data
            response = await func(*args, **kwargs)

            # Cache the response
            try:
                serialized = serialize_response(response)
                redis_client.setex(cache_key, expire, serialized)
            except Exception as e:
                print(f"Error caching response: {str(e)}")

            return response

        return wrapper

    return decorator


def clear_cache_by_prefix(prefix: str) -> bool:
    """
    Clear all cache entries with given prefix
    """
    try:
        pattern = f"{prefix}:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
        return True
    except Exception as e:
        print(f"Error clearing cache: {str(e)}")
        return False
