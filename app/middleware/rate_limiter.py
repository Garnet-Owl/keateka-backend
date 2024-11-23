from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Callable
from app.core.redis_client import redis_client


class RateLimiter:
    """Rate limiting middleware using Redis"""

    def __init__(
        self,
        times: int = 5,  # Number of requests allowed
        seconds: int = 60,  # Time window in seconds
    ):
        self.times = times
        self.seconds = seconds

    async def __call__(self, request: Request, call_next: Callable) -> JSONResponse:
        # Get client IP
        ip = request.client.host

        # Create a key for this IP
        key = f"rate_limit:{ip}"

        # Get current requests count
        requests = redis_client.get(key)

        if requests is None:
            # First request, set counter
            redis_client.setex(key, self.seconds, 1)
        else:
            requests = int(requests)
            if requests >= self.times:
                raise HTTPException(status_code=429, detail="Too many requests")
            redis_client.incr(key)

        response = await call_next(request)
        return response
