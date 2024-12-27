from typing import List, Optional

from fastapi import APIRouter, Depends, WebSocket, Query, BackgroundTasks
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.dependencies import (
    get_current_active_user,
)  # Fixed import
from app.api.auth.models import UserRole
from app.api.jobs import schemas, models
from app.api.jobs.exceptions import (
    CleanerNotAvailableError,
    JobSchedulingError,
)
from app.api.jobs.permissions import (
    check_job_permission,
    validate_cleaner_availability,
)
from app.api.jobs.repository import JobRepository
from app.api.jobs.time_tracking import TimeTrackingManager
from app.api.jobs.websocket import JobWebSocketManager
from app.api.notifications.service import NotificationService
from app.api.shared.database import get_db
from app.api.shared.middleware.rate_limiter import rate_limit
from app.api.shared.utils.cache import get_redis_client, CacheManager

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])
websocket_router = APIRouter(prefix="/api/v1/ws/jobs", tags=["jobs-websocket"])

# Initialize WebSocket manager
ws_manager = JobWebSocketManager()


# Dependencies
async def get_job_components(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
    notification_service: NotificationService = Depends(),
    current_user=Depends(get_current_active_user),
):
    """Get all job-related components."""
    cache_manager = CacheManager(redis, prefix="jobs")
    repository = JobRepository(db, cache_manager)
    time_tracking_manager = TimeTrackingManager(db, redis, notification_service)

    return {
        "repository": repository,
        "time_tracking": time_tracking_manager,
        "notification": notification_service,
        "current_user": current_user,
        "db": db,  # Added db to components for cleaner availability check
    }


# Job Management Routes
@router.post("/", response_model=schemas.JobResponse)
@rate_limit(limit=10, window=60)  # 10 job creations per minute
async def create_job(
    job_data: schemas.JobCreate,
    background_tasks: BackgroundTasks,
    components: dict = Depends(get_job_components),
):
    """Create a new job with rate limiting and validation."""
    current_user = components["current_user"]
    repository = components["repository"]

    # Verify business hours for scheduling
    if not await TimeTrackingManager.validate_business_hours(job_data.scheduled_time):
        raise JobSchedulingError("Job can only be scheduled during business hours")

    # Set client ID from authenticated user
    job_data.client_id = current_user.id

    # Create and save job
    job = await repository.save_job(models.Job(**job_data.dict()))

    # Schedule notifications in background
    background_tasks.add_task(
        components["notification"].send_notification,
        user_id=job.client_id,
        title="New Job Created",
        body=f"Job scheduled for {job.scheduled_time.strftime('%Y-%m-%d %H:%M')}",
    )

    return job


@router.get("/{job_id}", response_model=schemas.JobResponse)
@check_job_permission(allow_owner=True, check_cleaner=True)
async def get_job(job_id: int, components: dict = Depends(get_job_components)):
    """Get job details with caching and permission check."""
    repository = components["repository"]
    return await repository.get_job(job_id)


@router.put("/{job_id}", response_model=schemas.JobResponse)
@rate_limit(limit=20, window=60)  # 20 updates per minute
@check_job_permission(allow_owner=True)
async def update_job(
    job_id: int,
    job_data: schemas.JobUpdate,
    background_tasks: BackgroundTasks,
    components: dict = Depends(get_job_components),
):
    """Update job with rate limiting and real-time notifications."""
    repository = components["repository"]
    job = await repository.get_job(job_id)

    # Update job
    for field, value in job_data.dict(exclude_unset=True).items():
        setattr(job, field, value)

    updated_job = await repository.save_job(job)

    # Send real-time update via WebSocket
    background_tasks.add_task(ws_manager.broadcast_status_update, job_id, updated_job.dict())

    return updated_job


@router.delete("/{job_id}")
@check_job_permission(allow_owner=True)
async def delete_job(job_id: int, components: dict = Depends(get_job_components)):
    """Delete job with permission check."""
    repository = components["repository"]
    job = await repository.get_job(job_id)
    await repository.delete_job(job)
    return {"message": "Job deleted successfully"}


# Job Assignment Routes
@router.post("/{job_id}/assign/{cleaner_id}", response_model=schemas.JobResponse)
@check_job_permission(required_roles=[UserRole.ADMIN], allow_owner=True)
async def assign_cleaner(
    job_id: int,
    cleaner_id: int,
    background_tasks: BackgroundTasks,
    components: dict = Depends(get_job_components),
):
    """Assign cleaner with availability check and real-time notification."""
    repository = components["repository"]
    job = await repository.get_job(job_id)

    # Check cleaner availability
    if not await validate_cleaner_availability(
        components["db"],
        cleaner_id,
        job.scheduled_time,
        job.estimated_duration,
    ):
        raise CleanerNotAvailableError(cleaner_id)

    # Assign cleaner
    job.cleaner_id = cleaner_id
    job.status = models.JobStatus.ACCEPTED
    updated_job = await repository.save_job(job)

    # Send notifications
    background_tasks.add_task(
        components["notification"].send_notification,
        user_id=cleaner_id,
        title="New Job Assignment",
        body="You have been assigned to a new job",
    )

    # Send real-time update
    background_tasks.add_task(ws_manager.broadcast_status_update, job_id, updated_job.dict())

    return updated_job


# Time Tracking Routes
@router.post("/{job_id}/start", response_model=schemas.JobResponse)
@check_job_permission(check_cleaner=True)
async def start_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    components: dict = Depends(get_job_components),
):
    """Start job with time tracking and real-time updates."""
    repository = components["repository"]
    time_tracking = components["time_tracking"]

    job = await repository.get_job(job_id)
    tracking_result = await time_tracking.start_tracking(job)

    # Update job status
    job.status = models.JobStatus.IN_PROGRESS
    job.start_time = tracking_result["start_time"]
    updated_job = await repository.save_job(job)

    # Start real-time tracking updates
    background_tasks.add_task(ws_manager.broadcast_tracking_update, job_id, tracking_result)

    return updated_job


# WebSocket Routes
@websocket_router.websocket("/{job_id}/tracking")
async def job_tracking_websocket(
    websocket: WebSocket,
    job_id: int,
    current_user=Depends(get_current_active_user),
):
    """WebSocket endpoint for real-time job tracking updates."""
    try:
        await ws_manager.connect_client(websocket, job_id, str(current_user.id))

        try:
            while True:
                data = await websocket.receive_json()
                await ws_manager.handle_tracking_message(job_id, current_user.id, data)
        except Exception:
            # Handle WebSocket errors
            pass
        finally:
            await ws_manager.disconnect_client(job_id, str(current_user.id))
    except Exception:
        # Handle connection errors
        pass


# List Routes with Caching
@router.get("/client/jobs", response_model=List[schemas.JobResponse])
async def get_client_jobs(
    status: Optional[str] = Query(None),
    components: dict = Depends(get_job_components),
):
    """Get client jobs with caching."""
    repository = components["repository"]
    current_user = components["current_user"]
    return await repository.get_user_jobs(current_user.id, "client", status)


@router.get("/cleaner/jobs", response_model=List[schemas.JobResponse])
async def get_cleaner_jobs(
    status: Optional[str] = Query(None),
    components: dict = Depends(get_job_components),
):
    """Get cleaner jobs with caching."""
    repository = components["repository"]
    current_user = components["current_user"]
    return await repository.get_user_jobs(current_user.id, "cleaner", status)
