from datetime import datetime, timedelta
import select
from typing import Dict
from fastapi import HTTPException, status
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.jobs.models import Job, JobStatus
from app.features.jobs.time_tracking import TimeTracker
from app.shared.utils.time import TimeUtils
from app.shared.exceptions import BusinessLogicError, ValidationError
from app.shared.config import settings
from app.features.notifications.service import NotificationService


class TimeTrackingManager:
    """Manages job time tracking business logic."""

    def __init__(
        self,
        db: AsyncSession,
        redis_client: Redis,
        notification_service: NotificationService,
    ):
        self.db = db
        self.time_tracker = TimeTracker(redis_client)
        self.notification_service = notification_service

    async def validate_business_hours(self, job: Job) -> None:
        """Check if the job is within business hours."""
        current_time = TimeUtils.get_current_time()

        if not TimeUtils.is_business_hours(
            current_time,
            start_hour=settings.BUSINESS_HOURS_START,
            end_hour=settings.BUSINESS_HOURS_END,
        ):
            raise BusinessLogicError(
                "Jobs can only be started during business hours "
                f"({settings.BUSINESS_HOURS_START}:00 - {settings.BUSINESS_HOURS_END}:00)"
            )

    async def validate_job_schedule(self, job: Job) -> None:
        """Validate job scheduling constraints."""
        current_time = TimeUtils.get_current_time()

        # Check if job is scheduled for today
        if job.scheduled_time.date() != current_time.date():
            raise BusinessLogicError("Job can only be started on its scheduled date")

        # Check if within acceptable time window (30 mins before/after scheduled time)
        time_difference = abs((current_time - job.scheduled_time).total_seconds() / 60)
        if time_difference > 30:
            raise BusinessLogicError("Job can only be started within 30 minutes of scheduled time")

    async def check_concurrent_jobs(self, cleaner_id: int) -> None:
        """Check if cleaner has any active jobs."""
        active_jobs = await self.db.execute(
            select(Job).filter(
                Job.cleaner_id == cleaner_id,
                Job.status == JobStatus.IN_PROGRESS,
            )
        )
        if active_jobs.scalar_one_or_none():
            raise BusinessLogicError("Cleaner already has an active job")

    async def calculate_expected_end_time(self, job: Job) -> datetime:
        """Calculate expected end time based on estimated duration."""
        current_time = TimeUtils.get_current_time()
        return current_time + timedelta(minutes=job.estimated_duration)

    async def start_tracking(self, job: Job) -> Dict:
        """Start time tracking for a job."""
        try:
            # Validate constraints
            await self.validate_business_hours(job)
            await self.validate_job_schedule(job)
            await self.check_concurrent_jobs(job.cleaner_id)

            # Calculate expected end time
            expected_end_time = await self.calculate_expected_end_time(job)

            # Start tracking
            start_time = TimeUtils.get_current_time()
            await self.time_tracker.start_tracking(job.id, start_time)

            # Notify relevant parties
            await self._notify_tracking_start(job, expected_end_time)

            return {
                "start_time": start_time,
                "expected_end_time": expected_end_time,
                "estimated_duration": job.estimated_duration,
            }

        except (BusinessLogicError, ValidationError) as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start time tracking: {str(e)}",
            )

    async def stop_tracking(self, job: Job) -> Dict:
        """Stop time tracking for a job."""
        try:
            tracking_result = await self.time_tracker.stop_tracking(job.id)

            # Calculate final amount including any overtime
            final_amount = await self._calculate_final_amount(job, tracking_result["actual_duration"])
            tracking_result["final_amount"] = final_amount

            # Notify relevant parties
            await self._notify_tracking_stop(job, tracking_result)

            return tracking_result

        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to stop time tracking: {str(e)}",
            )

    async def pause_tracking(self, job: Job, reason: str) -> None:
        """Pause time tracking with a reason."""
        try:
            await self.time_tracker.pause_tracking(job.id)

            # Notify relevant parties
            await self._notify_tracking_pause(job, reason)

        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    async def resume_tracking(self, job: Job) -> None:
        """Resume time tracking."""
        try:
            await self.time_tracker.resume_tracking(job.id)

            # Get updated duration and expected end time
            current_status = await self.get_tracking_status(job)

            # Notify relevant parties
            await self._notify_tracking_resume(job, current_status)

        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    async def get_tracking_status(self, job: Job) -> Dict:
        """Get current tracking status with additional business logic."""
        try:
            status_data = await self.time_tracker.get_current_duration(job.id)

            # Add business-specific information
            status_data.update(
                {
                    "is_overtime": status_data["current_duration"] > job.estimated_duration,
                    "overtime_minutes": max(
                        0,
                        status_data["current_duration"] - job.estimated_duration,
                    ),
                    "estimated_completion": datetime.fromisoformat(status_data["start_time"])
                    + timedelta(minutes=job.estimated_duration),
                }
            )

            return status_data

        except ValidationError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active tracking session found",
            )

    async def _calculate_final_amount(self, job: Job, actual_duration: int) -> float:
        """Calculate final amount including overtime charges."""
        base_amount = job.base_rate * (job.estimated_duration / 60)  # Convert to hours

        # Calculate overtime if any
        overtime_minutes = max(0, actual_duration - job.estimated_duration)
        if overtime_minutes > 0:
            # 1.5x rate for overtime
            overtime_amount = (job.base_rate * 1.5) * (overtime_minutes / 60)
            return base_amount + overtime_amount

        return base_amount

    async def _notify_tracking_start(self, job: Job, expected_end_time: datetime) -> None:
        """Send notifications when tracking starts."""
        await self.notification_service.send_notification(
            user_id=job.client_id,
            title="Cleaning Service Started",
            body=f"Your cleaning service has started and is expected to end at {expected_end_time.strftime('%H:%M')}",
            data={
                "job_id": job.id,
                "event": "tracking_start",
                "expected_end_time": expected_end_time.isoformat(),
            },
        )

    async def _notify_tracking_stop(self, job: Job, tracking_result: Dict) -> None:
        """Send notifications when tracking stops."""
        await self.notification_service.send_notification(
            user_id=job.client_id,
            title="Cleaning Service Completed",
            body=f"Your cleaning service has been completed. Duration: {tracking_result['actual_duration']} minutes",
            data={
                "job_id": job.id,
                "event": "tracking_stop",
                "duration": tracking_result["actual_duration"],
                "final_amount": tracking_result["final_amount"],
            },
        )

    async def _notify_tracking_pause(self, job: Job, reason: str) -> None:
        """Send notifications when tracking is paused."""
        await self.notification_service.send_notification(
            user_id=job.client_id,
            title="Cleaning Service Paused",
            body=f"Your cleaning service has been paused. Reason: {reason}",
            data={
                "job_id": job.id,
                "event": "tracking_pause",
                "reason": reason,
            },
        )

    async def _notify_tracking_resume(self, job: Job, current_status: Dict) -> None:
        """Send notifications when tracking resumes."""
        await self.notification_service.send_notification(
            user_id=job.client_id,
            title="Cleaning Service Resumed",
            body="Your cleaning service has resumed",
            data={
                "job_id": job.id,
                "event": "tracking_resume",
                "current_duration": current_status["current_duration"],
                "estimated_completion": current_status["estimated_completion"].isoformat(),
            },
        )
