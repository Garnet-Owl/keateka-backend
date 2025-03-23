from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.jobs.models import Job, JobCreate, JobStatus, ScheduleSlot, ScheduleSlotCreate
from app.api.jobs.repository import JobRepository


class JobService:
    def __init__(self, db_session: AsyncSession):
        self.repository = JobRepository(db_session)
        # Base rate per minute in KES
        self.base_rate_per_minute = 4.50

    async def create_job(self, job_data: JobCreate, client_id: UUID) -> Job:
        # Calculate base cost based on estimated duration
        base_cost = self._calculate_base_cost(job_data.estimated_duration_minutes)

        # Create job entity
        job = Job(
            client_id=client_id,
            address=job_data.address,
            city=job_data.city,
            latitude=job_data.latitude,
            longitude=job_data.longitude,
            description=job_data.description,
            estimated_duration_minutes=job_data.estimated_duration_minutes,
            base_cost=base_cost,
            status=JobStatus.PENDING,
        )

        return await self.repository.create_job(job)

    def _calculate_base_cost(self, duration_minutes: int) -> float:
        """Calculate the base cost of a job based on estimated duration."""
        return duration_minutes * self.base_rate_per_minute

    async def get_job(self, job_id: UUID, include_slots: bool = False) -> Job:
        """Get a job by its ID."""
        job = await self.repository.get_job_by_id(job_id, include_slots)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    async def get_client_jobs(
        self, client_id: UUID, status: Optional[JobStatus] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[List[Job], int]:
        """Get all jobs for a client, with optional status filter."""
        return await self.repository.get_jobs_by_client(client_id=client_id, status=status, limit=limit, offset=offset)

    async def get_cleaner_jobs(
        self, cleaner_id: UUID, status: Optional[JobStatus] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[List[Job], int]:
        """Get all jobs for a cleaner, with optional status filter."""
        return await self.repository.get_jobs_by_cleaner(
            cleaner_id=cleaner_id, status=status, limit=limit, offset=offset
        )

    async def propose_schedule_slot(
        self, job_id: UUID, slot_data: ScheduleSlotCreate, proposed_by_cleaner: bool
    ) -> ScheduleSlot:
        """Propose a time slot for a job."""
        job = await self.repository.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Validate job status
        if job.status != JobStatus.PENDING and job.status != JobStatus.SCHEDULED:
            raise HTTPException(status_code=400, detail=f"Cannot propose schedule for job with status {job.status}")

        # Validate time slot
        if slot_data.start_time < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Cannot propose a time slot in the past")

        if slot_data.end_time <= slot_data.start_time:
            raise HTTPException(status_code=400, detail="End time must be after start time")

        # Calculate expected duration and verify it matches the job estimate
        slot_duration = (slot_data.end_time - slot_data.start_time).total_seconds() / 60
        if abs(slot_duration - job.estimated_duration_minutes) > 15:  # Allow 15 minutes flexibility
            raise HTTPException(
                status_code=400,
                detail=f"Proposed slot duration ({slot_duration}min) doesn't match job estimate ({job.estimated_duration_minutes}min)",
            )

        # Create the slot
        slot = ScheduleSlot(
            job_id=job_id,
            start_time=slot_data.start_time,
            end_time=slot_data.end_time,
            is_proposed_by_cleaner=proposed_by_cleaner,
        )

        return await self.repository.add_schedule_slot(slot)

    async def accept_schedule_slot(self, job_id: UUID, slot_id: UUID, client_id: UUID, cleaner_id: UUID) -> Job:
        """Accept a proposed time slot and assign the cleaner to the job."""
        job = await self.repository.get_job_by_id(job_id, include_slots=True)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Verify client ownership
        if job.client_id != client_id:
            raise HTTPException(status_code=403, detail="Not authorized to modify this job")

        # Find the slot
        slot = None
        for s in job.schedule_slots:
            if s.id == slot_id:
                slot = s
                break

        if not slot:
            raise HTTPException(status_code=404, detail="Schedule slot not found")

        if slot.is_accepted is not None:
            raise HTTPException(status_code=400, detail="This slot has already been processed")

        # Update the slot and job
        slot.is_accepted = True
        job.cleaner_id = cleaner_id
        job.status = JobStatus.SCHEDULED
        job.scheduled_for = slot.start_time

        return await self.repository.update_job(job)

    async def start_job(self, job_id: UUID, cleaner_id: UUID) -> Job:
        """Mark a job as started by the cleaner."""
        job = await self.repository.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Verify cleaner assignment
        if job.cleaner_id != cleaner_id:
            raise HTTPException(status_code=403, detail="Not authorized to start this job")

        # Validate job status
        if job.status != JobStatus.SCHEDULED:
            raise HTTPException(status_code=400, detail=f"Cannot start a job with status {job.status}")

        # Update job status
        job.status = JobStatus.IN_PROGRESS
        job.started_at = datetime.now(timezone.utc)

        return await self.repository.update_job(job)

    async def complete_job(self, job_id: UUID, cleaner_id: UUID, actual_duration_minutes: int) -> Job:
        """Mark a job as completed by the cleaner."""
        job = await self.repository.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Verify cleaner assignment
        if job.cleaner_id != cleaner_id:
            raise HTTPException(status_code=403, detail="Not authorized to complete this job")

        # Validate job status
        if job.status != JobStatus.IN_PROGRESS:
            raise HTTPException(status_code=400, detail=f"Cannot complete a job with status {job.status}")

        # Validate duration is reasonable
        if not job.started_at:
            raise HTTPException(status_code=500, detail="Job started_at timestamp missing")

        # Calculate the actual time elapsed since job start
        elapsed_minutes = (datetime.now(timezone.utc) - job.started_at).total_seconds() / 60

        # Allow some flexibility in reported duration, but flag large discrepancies
        # This could be refined with business rules
        if abs(actual_duration_minutes - elapsed_minutes) > 30:  # 30 min discrepancy
            # Could log this for review instead of failing
            pass

        # Calculate final cost based on actual duration
        final_cost = self._calculate_final_cost(job.base_cost, actual_duration_minutes, job.estimated_duration_minutes)

        # Update job
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        job.actual_duration_minutes = actual_duration_minutes
        job.final_cost = final_cost

        return await self.repository.update_job(job)

    def _calculate_final_cost(self, base_cost: float, actual_minutes: int, estimated_minutes: int) -> float:
        """
        Calculate the final cost of a job.
        For jobs that take longer than estimated, add charges for the extra time.
        """
        if actual_minutes <= estimated_minutes:
            return base_cost

        # Calculate extra time cost
        extra_minutes = actual_minutes - estimated_minutes
        extra_cost = extra_minutes * self.base_rate_per_minute * 1.2  # 20% premium for extra time

        return base_cost + extra_cost

    async def mark_job_paid(self, job_id: UUID) -> Job:
        """Mark a job as paid."""
        job = await self.repository.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Validate job status
        if job.status != JobStatus.COMPLETED:
            raise HTTPException(status_code=400, detail=f"Cannot mark as paid a job with status {job.status}")

        # Update job status
        job.status = JobStatus.PAID

        return await self.repository.update_job(job)

    async def cancel_job(self, job_id: UUID, user_id: UUID, is_client: bool) -> Job:
        """Cancel a job."""
        job = await self.repository.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Verify authorization
        if is_client and job.client_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to cancel this job")
        elif not is_client and job.cleaner_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to cancel this job")

        # Validate job status - can't cancel completed or paid jobs
        if job.status in [JobStatus.COMPLETED, JobStatus.PAID]:
            raise HTTPException(status_code=400, detail=f"Cannot cancel a job with status {job.status}")

        # Update job status
        job.status = JobStatus.CANCELED

        return await self.repository.update_job(job)

    async def get_available_jobs(self, limit: int = 50, offset: int = 0) -> List[Job]:
        """Get jobs that are available for cleaners to pick up."""
        return await self.repository.get_available_jobs(limit, offset)
