from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.notifications import send_notification
from app.database import get_db
from app.models.job import Job, JobStatus, JobReview
from app.models.user import User, UserType
from app.schemas.job import JobResponse, JobReviewCreate, JobReviewResponse
from app.utils.cache import cache_response

router = APIRouter()


@router.get("/", response_model=List[JobResponse])
@cache_response(prefix="jobs_list", expire=300)
def list_jobs(
    status: JobStatus = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    List jobs with optional filtering.
    """
    query = db.query(Job)

    if status:
        query = query.filter(Job.status == status)

    if current_user.user_type == UserType.CLIENT:
        query = query.filter(Job.client_id == current_user.id)
    elif current_user.user_type == UserType.CLEANER:
        # For cleaners, show available jobs and their assigned jobs
        query = query.filter(
            (Job.status == JobStatus.PENDING)
            | (Job.cleaner_id == current_user.id)
        )

    return query.offset(skip).limit(limit).all()


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get job by ID.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    # Check permissions
    if (
        current_user.user_type == UserType.CLIENT
        and job.client_id != current_user.id
    ) or (
        current_user.user_type == UserType.CLEANER
        and job.cleaner_id != current_user.id
        and job.status != JobStatus.PENDING
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    return job


@router.post("/{job_id}/accept", response_model=JobResponse)
def accept_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Cleaner accepts a job.
    """
    if current_user.user_type != UserType.CLEANER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only cleaners can accept jobs",
        )

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    if job.status != JobStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job cannot be accepted (current status: {job.status})",
        )

    job.status = JobStatus.ACCEPTED
    job.cleaner_id = current_user.id
    db.commit()
    db.refresh(job)

    # Send notification to client
    send_notification(
        user_id=job.client_id,
        title="Job Accepted",
        body=f"Your job has been accepted by {current_user.full_name}",
    )

    return job


@router.post("/{job_id}/start", response_model=JobResponse)
def start_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Start a job (cleaner marks job as started).
    """
    job = (
        db.query(Job)
        .filter(Job.id == job_id, Job.cleaner_id == current_user.id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    if job.status != JobStatus.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job cannot be started (current status: {job.status})",
        )

    job.status = JobStatus.IN_PROGRESS
    job.started_at = datetime.utcnow()
    db.commit()
    db.refresh(job)

    # Send notification to client
    send_notification(
        user_id=job.client_id,
        title="Job Started",
        body=f"Your cleaning service has been started by {current_user.full_name}",
    )

    return job


@router.post("/{job_id}/complete", response_model=JobResponse)
def complete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Complete a job (cleaner marks job as completed).
    """
    job = (
        db.query(Job)
        .filter(Job.id == job_id, Job.cleaner_id == current_user.id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    if job.status != JobStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job cannot be completed (current status: {job.status})",
        )

    job.status = JobStatus.COMPLETED
    job.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(job)

    # Send notification to client
    send_notification(
        user_id=job.client_id,
        title="Job Completed",
        body=f"Your cleaning service has been completed by {current_user.full_name}",
    )

    return job


@router.post("/{job_id}/review", response_model=JobReviewResponse)
def create_review(
    job_id: int,
    review: JobReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create a review for a completed job.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only review completed jobs",
        )

    # Check if user is either the client or cleaner
    if current_user.id not in [job.client_id, job.cleaner_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only job participants can leave reviews",
        )

    # Check if user already left a review
    existing_review = (
        db.query(JobReview)
        .filter(
            JobReview.job_id == job_id,
            JobReview.reviewer_id == current_user.id,
        )
        .first()
    )

    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this job",
        )

    review_db = JobReview(
        job_id=job_id, reviewer_id=current_user.id, **review.model_dump()
    )
    db.add(review_db)
    db.commit()
    db.refresh(review_db)

    # Send notification
    notify_user_id = (
        job.cleaner_id if current_user.id == job.client_id else job.client_id
    )
    send_notification(
        user_id=notify_user_id,
        title="New Review",
        body=f"You have received a new review for job #{job_id}",
    )

    return review_db
