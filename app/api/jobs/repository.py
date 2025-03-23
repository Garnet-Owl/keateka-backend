from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.jobs.models import Job, JobStatus, ScheduleSlot


class JobRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_job(self, job: Job) -> Job:
        self.db_session.add(job)
        await self.db_session.commit()
        await self.db_session.refresh(job)
        return job

    async def get_job_by_id(self, job_id: UUID, include_slots: bool = False) -> Optional[Job]:
        query = select(Job).where(Job.id == job_id)

        if include_slots:
            query = query.options(selectinload(Job.schedule_slots))

        result = await self.db_session.execute(query)
        return result.scalars().first()

    async def get_jobs_by_client(
        self, client_id: UUID, status: Optional[JobStatus] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[List[Job], int]:
        query = select(Job).where(Job.client_id == client_id)

        if status:
            query = query.where(Job.status == status)

        # Get total count
        count_query = select(Job.id).where(Job.client_id == client_id)
        if status:
            count_query = count_query.where(Job.status == status)
        count_result = await self.db_session.execute(count_query)
        total_count = len(count_result.scalars().all())

        # Apply pagination
        query = query.order_by(desc(Job.created_at)).limit(limit).offset(offset)

        result = await self.db_session.execute(query)
        return result.scalars().all(), total_count

    async def get_jobs_by_cleaner(
        self, cleaner_id: UUID, status: Optional[JobStatus] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[List[Job], int]:
        query = select(Job).where(Job.cleaner_id == cleaner_id)

        if status:
            query = query.where(Job.status == status)

        # Get total count
        count_query = select(Job.id).where(Job.cleaner_id == cleaner_id)
        if status:
            count_query = count_query.where(Job.status == status)
        count_result = await self.db_session.execute(count_query)
        total_count = len(count_result.scalars().all())

        # Apply pagination
        query = query.order_by(desc(Job.created_at)).limit(limit).offset(offset)

        result = await self.db_session.execute(query)
        return result.scalars().all(), total_count

    async def update_job(self, job: Job) -> Job:
        await self.db_session.commit()
        await self.db_session.refresh(job)
        return job

    async def add_schedule_slot(self, slot: ScheduleSlot) -> ScheduleSlot:
        self.db_session.add(slot)
        await self.db_session.commit()
        await self.db_session.refresh(slot)
        return slot

    async def get_slot_by_id(self, slot_id: UUID) -> Optional[ScheduleSlot]:
        query = select(ScheduleSlot).where(ScheduleSlot.id == slot_id)
        result = await self.db_session.execute(query)
        return result.scalars().first()

    async def get_available_slots_for_job(self, job_id: UUID) -> List[ScheduleSlot]:
        query = select(ScheduleSlot).where(
            and_(
                ScheduleSlot.job_id == job_id,
                ScheduleSlot.is_accepted.is_(None),  # Only pending slots
            )
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def get_available_jobs(self, limit: int = 50, offset: int = 0) -> List[Job]:
        """Get jobs that are pending assignment to a cleaner."""
        query = select(Job).where(Job.status == JobStatus.PENDING)
        query = query.order_by(desc(Job.created_at)).limit(limit).offset(offset)
        result = await self.db_session.execute(query)
        return result.scalars().all()
