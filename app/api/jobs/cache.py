import json
from typing import Optional
from uuid import UUID

from redis.asyncio import Redis

from app.api.jobs.models import Job, JobResponse


class JobCache:
    """Cache implementation for job-related data using Redis."""

    def __init__(self, redis: Redis):
        self.redis = redis
        self.key_prefix = "jobs:"
        self.ttl = 3600  # 1 hour TTL by default

    async def get_job(self, job_id: UUID) -> Optional[JobResponse]:
        """Get a job from cache by ID."""
        key = f"{self.key_prefix}{job_id}"
        data = await self.redis.get(key)

        if not data:
            return None

        try:
            job_dict = json.loads(data)
            return JobResponse.model_validate(job_dict)
        except Exception:
            # If deserialization fails, remove the invalid cache entry
            await self.redis.delete(key)
            return None

    async def set_job(self, job: Job, ttl: Optional[int] = None) -> None:
        """Store a job in cache."""
        key = f"{self.key_prefix}{job.id}"
        job_data = JobResponse.model_validate(job).model_dump()

        # Store as JSON string
        await self.redis.set(key, json.dumps(job_data), ex=ttl or self.ttl)

    async def invalidate_job(self, job_id: UUID) -> None:
        """Remove a job from cache."""
        key = f"{self.key_prefix}{job_id}"
        await self.redis.delete(key)

    async def get_available_jobs_count(self) -> int:
        """Get the count of available jobs from cache."""
        count = await self.redis.get(f"{self.key_prefix}available_count")
        return int(count) if count else 0

    async def set_available_jobs_count(self, count: int, ttl: Optional[int] = None) -> None:
        """Set the count of available jobs in cache."""
        await self.redis.set(f"{self.key_prefix}available_count", count, ex=ttl or self.ttl)
