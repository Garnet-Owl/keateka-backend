from datetime import timedelta, datetime
from functools import wraps
from typing import Callable

from fastapi import Depends
from sqlalchemy import select

from app.features.auth.dependencies import get_current_active_user
from app.features.auth.models import UserRole
from app.features.jobs.exceptions import (
    JobAuthorizationError,
    JobNotFoundException,
)
from app.features.jobs.models import Job, JobStatus
from app.features.jobs.routes import get_job
from app.shared.database import AsyncSession, get_db


def check_job_permission(
    required_roles: list[UserRole] = None,
    allow_owner: bool = True,
    check_cleaner: bool = False,
):
    """Decorator to check job permissions."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user and job
            current_user = kwargs.get("current_user")
            job_id = kwargs.get("job_id")
            db = kwargs.get("db")

            # Verify role permissions
            if required_roles and current_user.role not in required_roles:
                raise JobAuthorizationError("Insufficient permissions")

            # Get job
            job = await get_job(db, job_id)
            if not job:
                raise JobNotFoundException(job_id)

            # Check ownership
            if allow_owner and job.client_id == current_user.id:
                return await func(*args, **kwargs)

            # Check if user is assigned cleaner
            if check_cleaner and job.cleaner_id == current_user.id:
                return await func(*args, **kwargs)

            raise JobAuthorizationError()

        return wrapper

    return decorator


async def validate_cleaner_availability(
    db: AsyncSession,
    cleaner_id: int,
    scheduled_time: datetime,
    estimated_duration: int,
) -> bool:
    """Check if cleaner is available for the job time slot."""
    # Get cleaner's jobs for the day
    day_start = scheduled_time.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    overlapping_jobs = await db.execute(
        select(Job).filter(
            Job.cleaner_id == cleaner_id,
            Job.scheduled_time >= day_start,
            Job.scheduled_time < day_end,
            Job.status.in_([JobStatus.ACCEPTED, JobStatus.IN_PROGRESS]),
        )
    )
    jobs = overlapping_jobs.scalars().all()

    # Check for time conflicts
    job_end_time = scheduled_time + timedelta(minutes=estimated_duration)

    for existing_job in jobs:
        existing_end_time = existing_job.scheduled_time + timedelta(minutes=existing_job.estimated_duration)

        if (
            (scheduled_time <= existing_job.scheduled_time < job_end_time)
            or (scheduled_time < existing_end_time <= job_end_time)
            or (existing_job.scheduled_time <= scheduled_time < existing_end_time)
        ):
            return False

    return True


# Permission check dependencies
async def check_client_permission(
    job_id: int,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Job:
    """Check if current user has client permission for the job."""
    job = await get_job(db, job_id)
    if job.client_id != current_user.id:
        raise JobAuthorizationError("Not authorized to access this job")
    return job


async def check_cleaner_permission(
    job_id: int,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Job:
    """Check if current user has cleaner permission for the job."""
    job = await get_job(db, job_id)
    if job.cleaner_id != current_user.id:
        raise JobAuthorizationError("Not authorized to access this job")
    return job


async def check_admin_permission(
    current_user=Depends(get_current_active_user),
) -> None:
    """Check if current user has admin permissions."""
    if current_user.role != UserRole.ADMIN:
        raise JobAuthorizationError("Admin permissions required")
