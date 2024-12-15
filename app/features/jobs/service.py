from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.features.jobs import models, schemas
from app.features.jobs.time_tracking import TimeTrackingManager
from app.shared.exceptions import NotFoundException, BusinessLogicError
from app.features.notifications.service import NotificationService
from app.shared.utils.time import TimeUtils


class JobService:
    def __init__(
        self,
        db: AsyncSession,
        time_tracking_manager: Optional[TimeTrackingManager] = None,
        notification_service: Optional[NotificationService] = None,
    ):
        self.db = db
        self.time_tracking_manager = time_tracking_manager
        self.notification_service = notification_service

    async def create_job(self, job_data: schemas.JobCreate) -> models.Job:
        """Create a new job."""
        # Validate scheduled time
        scheduled_time = TimeUtils.parse_datetime(job_data.scheduled_time)
        if scheduled_time < TimeUtils.get_current_time():
            raise BusinessLogicError("Cannot schedule job in the past")

        job = models.Job(**job_data.dict())
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        if self.notification_service:
            await self.notification_service.send_notification(
                user_id=job.client_id,
                title="New Job Created",
                body=f"Job scheduled for {scheduled_time.strftime('%Y-%m-%d %H:%M')}",
                data={"job_id": job.id, "event": "job_created"},
            )

        return job

    async def get_job(self, job_id: int) -> Optional[models.Job]:
        """Get job by ID."""
        result = await self.db.execute(select(models.Job).filter(models.Job.id == job_id))
        job = result.scalar_one_or_none()

        if not job:
            raise NotFoundException(f"Job with id {job_id} not found")
        return job

    async def update_job(self, job_id: int, job_data: schemas.JobUpdate) -> models.Job:
        """Update job details."""
        job = await self.get_job(job_id)

        # Validate status transition
        if job_data.status:
            await self._validate_status_transition(job, job_data.status)

        # Update fields
        for field, value in job_data.dict(exclude_unset=True).items():
            setattr(job, field, value)

        await self.db.commit()
        await self.db.refresh(job)

        # Send notification if status changed
        if job_data.status and self.notification_service:
            await self.notification_service.send_notification(
                user_id=job.client_id,
                title="Job Status Updated",
                body=f"Job status changed to {job_data.status}",
                data={
                    "job_id": job.id,
                    "event": "status_changed",
                    "status": job_data.status,
                },
            )

        return job

    async def delete_job(self, job_id: int) -> None:
        """Delete a job."""
        job = await self.get_job(job_id)

        # Can only delete pending jobs
        if job.status != models.JobStatus.PENDING:
            raise BusinessLogicError("Only pending jobs can be deleted")

        await self.db.delete(job)
        await self.db.commit()

        if self.notification_service:
            await self.notification_service.send_notification(
                user_id=job.client_id,
                title="Job Deleted",
                body="Your scheduled job has been deleted",
                data={"job_id": job_id, "event": "job_deleted"},
            )

    async def get_jobs_by_client(self, client_id: int, status: Optional[str] = None) -> List[models.Job]:
        """Get all jobs for a client with optional status filter."""
        query = select(models.Job).filter(models.Job.client_id == client_id)
        if status:
            query = query.filter(models.Job.status == status)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_jobs_by_cleaner(self, cleaner_id: int, status: Optional[str] = None) -> List[models.Job]:
        """Get all jobs for a cleaner with optional status filter."""
        query = select(models.Job).filter(models.Job.cleaner_id == cleaner_id)
        if status:
            query = query.filter(models.Job.status == status)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def assign_cleaner(self, job_id: int, cleaner_id: int) -> Tuple[models.Job, bool]:
        """Assign a cleaner to a job."""
        job = await self.get_job(job_id)

        if job.status != models.JobStatus.PENDING:
            raise BusinessLogicError("Can only assign cleaners to pending jobs")

        if job.cleaner_id:
            raise BusinessLogicError("Job already has an assigned cleaner")

        # Update job
        job.cleaner_id = cleaner_id
        job.status = models.JobStatus.ACCEPTED
        await self.db.commit()
        await self.db.refresh(job)

        if self.notification_service:
            # Notify client
            await self.notification_service.send_notification(
                user_id=job.client_id,
                title="Cleaner Assigned",
                body="A cleaner has been assigned to your job",
                data={"job_id": job.id, "event": "cleaner_assigned"},
            )

        return job, True

    async def start_job(self, job_id: int) -> models.Job:
        """Start a job and begin time tracking."""
        if not self.time_tracking_manager:
            raise BusinessLogicError("Time tracking is not configured")

        job = await self.get_job(job_id)

        if job.status != models.JobStatus.ACCEPTED:
            raise BusinessLogicError("Only accepted jobs can be started")

        # Start time tracking
        tracking_result = await self.time_tracking_manager.start_tracking(job)

        # Update job status and start time
        job.status = models.JobStatus.IN_PROGRESS
        job.start_time = tracking_result["start_time"]
        await self.db.commit()
        await self.db.refresh(job)

        return job

    async def complete_job(self, job_id: int) -> models.Job:
        """Complete a job and finalize time tracking."""
        if not self.time_tracking_manager:
            raise BusinessLogicError("Time tracking is not configured")

        job = await self.get_job(job_id)

        if job.status != models.JobStatus.IN_PROGRESS:
            raise BusinessLogicError("Only in-progress jobs can be completed")

        # Stop time tracking and get final details
        tracking_result = await self.time_tracking_manager.stop_tracking(job)

        # Update job with final details
        job.status = models.JobStatus.COMPLETED
        job.end_time = tracking_result["end_time"]
        job.actual_duration = tracking_result["actual_duration"]
        job.final_amount = tracking_result["final_amount"]
        await self.db.commit()
        await self.db.refresh(job)

        return job

    async def _validate_status_transition(self, job: models.Job, new_status: str) -> None:
        """Validate if the status transition is allowed."""
        valid_transitions = {
            models.JobStatus.PENDING: [
                models.JobStatus.ACCEPTED,
                models.JobStatus.CANCELLED,
            ],
            models.JobStatus.ACCEPTED: [
                models.JobStatus.IN_PROGRESS,
                models.JobStatus.CANCELLED,
            ],
            models.JobStatus.IN_PROGRESS: [
                models.JobStatus.COMPLETED,
                models.JobStatus.CANCELLED,
            ],
            models.JobStatus.COMPLETED: [],  # No transitions allowed from completed
            models.JobStatus.CANCELLED: [],  # No transitions allowed from cancelled
        }

        if new_status not in valid_transitions.get(job.status, []):
            raise BusinessLogicError(f"Invalid status transition from {job.status} to {new_status}")
