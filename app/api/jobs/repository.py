from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
from app.api.jobs.models import Job
from app.api.shared.utils.cache import CacheManager
from app.api.shared.exceptions import NotFoundException


class JobRepository:
    def __init__(self, db: AsyncSession, cache_manager: CacheManager):
        self.db = db
        self.cache = cache_manager
        self.cache_ttl = timedelta(minutes=15)  # Default cache TTL

    async def get_job(self, job_id: int) -> Optional[Job]:
        """Get job by ID with caching."""
        cache_key = f"job:{job_id}"

        # Try to get from cache
        cached_job = await self.cache.get(cache_key)
        if cached_job:
            return cached_job

        # Get from database
        result = await self.db.execute(select(Job).filter(Job.id == job_id))
        job = result.scalar_one_or_none()

        if job:
            # Cache the job
            await self.cache.set(cache_key, job, expires_in=self.cache_ttl)
            return job

        raise NotFoundException(f"Job with id {job_id} not found")

    async def get_user_jobs(self, user_id: int, role: str, status: Optional[str] = None) -> List[Job]:
        """Get user's jobs with caching."""
        cache_key = f"user:{user_id}:jobs:{role}"
        if status:
            cache_key += f":{status}"

        # Try to get from cache
        cached_jobs = await self.cache.get(cache_key)
        if cached_jobs:
            return cached_jobs

        # Build query based on role
        query = select(Job)
        if role == "client":
            query = query.filter(Job.client_id == user_id)
        elif role == "cleaner":
            query = query.filter(Job.cleaner_id == user_id)

        if status:
            query = query.filter(Job.status == status)

        # Get from database
        result = await self.db.execute(query)
        jobs = result.scalars().all()

        # Cache the results
        await self.cache.set(cache_key, jobs, expires_in=self.cache_ttl)
        return jobs

    async def invalidate_job_cache(self, job_id: int):
        """Invalidate job cache."""
        cache_key = f"job:{job_id}"
        await self.cache.delete(cache_key)

    async def invalidate_user_jobs_cache(self, user_id: int):
        """Invalidate user's jobs cache."""
        patterns = [
            f"user:{user_id}:jobs:client*",
            f"user:{user_id}:jobs:cleaner*",
        ]
        for pattern in patterns:
            await self.cache.delete_pattern(pattern)

    async def save_job(self, job: Job) -> Job:
        """Save job and update cache."""
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        # Update cache
        cache_key = f"job:{job.id}"
        await self.cache.set(cache_key, job, expires_in=self.cache_ttl)

        # Invalidate user jobs cache
        await self.invalidate_user_jobs_cache(job.client_id)
        if job.cleaner_id:
            await self.invalidate_user_jobs_cache(job.cleaner_id)

        return job

    async def delete_job(self, job: Job):
        """Delete job and clear cache."""
        await self.db.delete(job)
        await self.db.commit()

        # Clear cache
        await self.invalidate_job_cache(job.id)
        await self.invalidate_user_jobs_cache(job.client_id)
        if job.cleaner_id:
            await self.invalidate_user_jobs_cache(job.cleaner_id)
