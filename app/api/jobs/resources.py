from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.dependencies import get_current_user
from app.api.auth.models import User, UserRole
from app.api.jobs.models import (
    JobCompleteRequest,
    JobCreate,
    JobResponse,
    JobStartRequest,
    JobStatus,
    ScheduleJobRequest,
    ScheduleSlotCreate,
    ScheduleSlotResponse,
)
from app.api.jobs.service import JobService
from app.api.storage.dependencies import get_db

router = APIRouter(prefix="/jobs", tags=["jobs"])


# Helper function for pagination responses
def create_paginated_response(items, total, limit, offset):
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Create a new cleaning job."""
    service = JobService(db)
    job = await service.create_job(job_data, current_user.id)
    return job


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    include_slots: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a job by ID."""
    service = JobService(db)
    job = await service.get_job(job_id, include_slots)

    # Only client, assigned cleaner, or admins can view job details
    if current_user.id != job.client_id and current_user.id != job.cleaner_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this job")

    return job


@router.get("")
async def list_jobs(
    job_status: Optional[JobStatus] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List jobs for the current user based on their role."""
    service = JobService(db)

    if current_user.role == UserRole.CLIENT:
        jobs, total = await service.get_client_jobs(
            client_id=current_user.id, status=job_status, limit=limit, offset=offset
        )
        return create_paginated_response(jobs, total, limit, offset)
    elif current_user.role == UserRole.CLEANER:
        jobs, total = await service.get_cleaner_jobs(
            cleaner_id=current_user.id, status=job_status, limit=limit, offset=offset
        )
        return create_paginated_response(jobs, total, limit, offset)
    elif current_user.role == UserRole.ADMIN:
        # For admins, return all jobs or implement admin-specific filtering
        # This is simplified and should be implemented based on requirements
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Admin job listing not implemented")

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to list jobs")


@router.get("/available")
async def list_available_jobs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List jobs available for cleaners to accept."""
    if current_user.role != UserRole.CLEANER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only cleaners can view available jobs")

    service = JobService(db)
    jobs = await service.get_available_jobs(limit=limit, offset=offset)
    # For available jobs, we don't have a total count method implemented yet
    # Using len(jobs) as a simplification
    return create_paginated_response(jobs, len(jobs), limit, offset)


@router.post("/schedule-slot", response_model=ScheduleSlotResponse)
async def propose_schedule_slot(
    slot_data: ScheduleSlotCreate,
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Propose a time slot for a job."""
    service = JobService(db)

    # Verify the job exists and get its details
    job = await service.get_job(job_id)

    # Check authorization to propose slots
    is_cleaner_proposal = current_user.role == UserRole.CLEANER
    is_client_proposal = current_user.id == job.client_id

    if not (is_cleaner_proposal or is_client_proposal):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to propose schedule slots for this job"
        )

    # Create the slot
    return await service.propose_schedule_slot(
        job_id=job_id, slot_data=slot_data, proposed_by_cleaner=is_cleaner_proposal
    )


@router.post("/accept-schedule", response_model=JobResponse)
async def accept_schedule(
    data: ScheduleJobRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Accept a proposed schedule and assign cleaner to job."""
    service = JobService(db)

    # Get the job to verify ownership
    job = await service.get_job(data.job_id, include_slots=True)

    # Only the client can accept schedules
    if current_user.id != job.client_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the client can accept schedules")

    # Find the slot to get the cleaner_id if it was proposed by a cleaner
    cleaner_id = None
    for slot in job.schedule_slots:
        if slot.id == data.slot_id and slot.is_proposed_by_cleaner:
            # In a real implementation, you would get the cleaner_id from the slot
            # or have it included in the request
            # For now, using a placeholder approach
            cleaner_id = UUID("00000000-0000-0000-0000-000000000000")  # Placeholder
            break

    if not cleaner_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid slot or cleaner information")

    # Accept the slot and update the job
    return await service.accept_schedule_slot(
        job_id=data.job_id, slot_id=data.slot_id, client_id=current_user.id, cleaner_id=cleaner_id
    )


@router.post("/start", response_model=JobResponse)
async def start_job(
    data: JobStartRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Start a job."""
    if current_user.role != UserRole.CLEANER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only cleaners can start jobs")

    service = JobService(db)
    return await service.start_job(job_id=data.job_id, cleaner_id=current_user.id)


@router.post("/complete", response_model=JobResponse)
async def complete_job(
    data: JobCompleteRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Complete a job."""
    if current_user.role != UserRole.CLEANER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only cleaners can complete jobs")

    service = JobService(db)
    return await service.complete_job(
        job_id=data.job_id, cleaner_id=current_user.id, actual_duration_minutes=data.actual_duration_minutes
    )


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(job_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Cancel a job."""
    service = JobService(db)

    # Get the job to check ownership
    job = await service.get_job(job_id)

    is_client = current_user.id == job.client_id
    is_assigned_cleaner = current_user.id == job.cleaner_id

    if not (is_client or is_assigned_cleaner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only the client or assigned cleaner can cancel this job"
        )

    return await service.cancel_job(job_id=job_id, user_id=current_user.id, is_client=is_client)
