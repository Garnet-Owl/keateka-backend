from functools import wraps
import time
from typing import Optional

from fastapi import HTTPException, Request
from redis import Redis


class RateLimiter:
    """Rate limiter using Redis as backend."""

    def __init__(
        self, redis_client: Redis, key_prefix: str = "rate_limit"
    ) -> None:
        self.redis = redis_client
        self.key_prefix = key_prefix

    async def _generate_key(
        self, request: Request, key_type: str = "ip"
    ) -> str:
        """Generate a unique key for rate limiting."""
        if key_type == "ip":
            key = request.client.host
        elif key_type == "user":
            # Assume user ID is in request state after auth
            key = (
                str(request.state.user_id)
                if hasattr(request.state, "user_id")
                else request.client.host
            )
        else:
            key = request.client.host

        return f"{self.key_prefix}:{key}:{request.url.path}"

    async def is_rate_limited(
        self,
        request: Request,
        limit: int = 100,
        window: int = 60,
        key_type: str = "ip",
    ) -> bool:
        """
        Check if the request is rate limited.

        Args:
            request: FastAPI request object
            limit: Maximum number of requests allowed in the window
            window: Time window in seconds
            key_type: Type of key to use for rate limiting ("ip" or "user")
        """
        key = await self._generate_key(request, key_type)
        current_time = int(time.time())
        window_start = current_time - window

        pipeline = self.redis.pipeline()
        # Remove old requests
        pipeline.zremrangebyscore(key, 0, window_start)
        # Add current request
        pipeline.zadd(key, {str(current_time): current_time})
        # Count requests in window
        pipeline.zcount(key, window_start, current_time)
        # Set expiry on the key
        pipeline.expire(key, window)

        _, _, request_count, _ = await pipeline.execute()

        return request_count > limit


def rate_limit(
    limit: int = 100,
    window: int = 60,
    key_type: str = "ip",
    redis_client: Optional[Redis] = None,
):
    """
    Rate limiting decorator for FastAPI endpoints.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request object in args or kwargs
            request = next(
                (arg for arg in args if isinstance(arg, Request)),
                next(
                    (v for v in kwargs.values() if isinstance(v, Request)),
                    None,
                ),
            )

            if not request:
                # If no request found, inject it
                request = Request

            if not redis_client:
                raise HTTPException(
                    status_code=500,
                    detail="Rate limiter not properly configured",
                )

            limiter = RateLimiter(redis_client)
            is_limited = await limiter.is_rate_limited(
                request, limit, window, key_type
            )

            if is_limited:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Try again in {window} seconds.",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
