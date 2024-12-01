from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user
from app.database import get_db
from app.models.job import Job, JobStatus, PaymentStatus
from app.models.user import User, UserType
from app.schemas.job import JobCreate, JobResponse, JobUpdate
from app.services.matching import matching_service
from app.utils.cache import cache_response

router = APIRouter()


@router.post(
    "/", response_model=JobResponse, status_code=status.HTTP_201_CREATED
)
def create_job(
    *,
    db: Session = Depends(get_db),
    job_in: JobCreate,
    current_user: User = Depends(get_current_user),
) -> Job:
    """Create a new job posting. Only clients can create jobs."""
    if current_user.user_type != UserType.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can create jobs",
        )

    if not job_in.scheduled_at.tzinfo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scheduled time must include timezone information",
        )

    # Create job using model_dump to ensure field compatibility
    job_data = job_in.model_dump()
    job_data.update(
        {
            "client_id": current_user.id,
            "status": JobStatus.PENDING,
            "payment_status": PaymentStatus.PENDING,
            "total_amount": float(
                job_in.duration_hours * job_in.rate_per_hour
            ),
        }
    )

    job = Job(**job_data)

    db.add(job)
    db.commit()
    db.refresh(job)

    # Update matches
    matching_service.db = db
    matching_service.find_matches_for_job(job.id)

    return job


@router.get("/search", response_model=List[JobResponse])
@cache_response(prefix="jobs_search", expire=300)
def search_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: Optional[JobStatus] = None,
    min_rate: Optional[float] = None,
    max_rate: Optional[float] = None,
    location: Optional[str] = None,
    scheduled_after: Optional[datetime] = None,
    scheduled_before: Optional[datetime] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
) -> List[Job]:
    """Search for jobs with various filters."""
    query = db.query(Job).options(
        joinedload(Job.client),
        joinedload(Job.cleaner),
        joinedload(Job.reviews),
    )

    # Base filters based on user type
    if current_user.user_type == UserType.CLIENT:
        query = query.filter(Job.client_id == current_user.id)
    elif current_user.user_type == UserType.CLEANER:
        query = query.filter(
            or_(
                and_(
                    Job.status == JobStatus.PENDING, Job.cleaner_id.is_(None)
                ),
                Job.cleaner_id == current_user.id,
            )
        )

    # Apply search filters
    if status:
        query = query.filter(Job.status == status)
    if min_rate is not None:
        query = query.filter(Job.rate_per_hour >= min_rate)
    if max_rate is not None:
        query = query.filter(Job.rate_per_hour <= max_rate)
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    if scheduled_after:
        if not scheduled_after.tzinfo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scheduled after time must include timezone information",
            )
        query = query.filter(Job.scheduled_at >= scheduled_after)
    if scheduled_before:
        if not scheduled_before.tzinfo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scheduled before time must include timezone information",
            )
        query = query.filter(Job.scheduled_at <= scheduled_before)

    # Order and paginate
    query = query.order_by(Job.created_at.desc())
    jobs = query.offset(skip).limit(limit).all()
    return list(jobs)


@router.get("/recommendations", response_model=List[JobResponse])
@cache_response(prefix="jobs_recommendations", expire=300)
def get_job_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=5, ge=1, le=20),
) -> List[Job]:
    """Get job recommendations for cleaners based on their profile."""
    if current_user.user_type != UserType.CLEANER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only cleaners can get job recommendations",
        )

    matching_service.db = db
    recommendations = matching_service.suggest_jobs_for_cleaner(
        cleaner_id=current_user.id, max_suggestions=limit
    )

    return [job for job, _ in recommendations]


@router.put("/{job_id}", response_model=JobResponse)
def update_job(
    *,
    db: Session = Depends(get_db),
    job_id: int,
    job_in: JobUpdate,
    current_user: User = Depends(get_current_user),
) -> Job:
    """Update job details. Only the job creator can update the job."""
    job = (
        db.query(Job)
        .filter(Job.id == job_id, Job.client_id == current_user.id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or you don't have permission to update it",
        )

    if job.status != JobStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending jobs can be updated",
        )

    if job_in.scheduled_at and not job_in.scheduled_at.tzinfo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scheduled time must include timezone information",
        )

    # Update fields
    update_data = job_in.model_dump(exclude_unset=True)

    # Handle special calculations
    if "duration_hours" in update_data or "rate_per_hour" in update_data:
        duration = update_data.get("duration_hours", job.duration_hours)
        rate = update_data.get("rate_per_hour", job.rate_per_hour)
        update_data["total_amount"] = float(duration) * float(rate)

    for field, value in update_data.items():
        setattr(job, field, value)

    db.commit()
    db.refresh(job)

    matching_service.db = db
    matching_service.find_matches_for_job(job.id)

    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    *,
    db: Session = Depends(get_db),
    job_id: int,
    current_user: User = Depends(get_current_user),
) -> None:
    """Cancel/Delete a job. Only the job creator can cancel the job."""
    job = (
        db.query(Job)
        .filter(Job.id == job_id, Job.client_id == current_user.id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or you don't have permission to delete it",
        )

    if job.status not in [JobStatus.PENDING, JobStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or cancelled jobs can be deleted",
        )

    db.delete(job)
    db.commit()
