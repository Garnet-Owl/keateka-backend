from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from hamcrest import assert_that, equal_to, is_, not_none

from app.api.jobs.models import Job, JobStatus, ScheduleSlot
from app.api.jobs.service import JobService
from app.tests.givenpy import given, then, when


def prepare_job_service():
    """Prepare job service with mocked dependencies."""

    def step(context):
        context.async_session = AsyncMock()
        context.repository = AsyncMock()

        # Create a job service with mocked repository
        context.job_service = JobService(context.async_session)
        context.job_service.repository = context.repository

    return step


def prepare_job_data():
    """Prepare test job data."""

    def step(context):
        context.client_id = uuid4()
        context.cleaner_id = uuid4()
        context.job_id = uuid4()
        context.slot_id = uuid4()

        context.job_data = {
            "address": "123 Test Street",
            "city": "Test City",
            "latitude": 1.2345,
            "longitude": 6.7890,
            "description": "Test cleaning job",
            "estimated_duration_minutes": 120,
        }

        context.slot_data = {
            "start_time": datetime.now(timezone.utc) + timedelta(days=1),
            "end_time": datetime.now(timezone.utc) + timedelta(days=1, hours=2),
        }

        # Create a sample job object
        context.job = Job(
            id=context.job_id,
            client_id=context.client_id,
            cleaner_id=None,
            status=JobStatus.PENDING,
            address=context.job_data["address"],
            city=context.job_data["city"],
            latitude=context.job_data["latitude"],
            longitude=context.job_data["longitude"],
            description=context.job_data["description"],
            estimated_duration_minutes=context.job_data["estimated_duration_minutes"],
            base_cost=1200.0,  # 120 minutes * 10 base rate
        )

    return step


def prepare_mock_repository():
    """Prepare repository mock responses."""

    def step(context):
        # Setup repository method mocks
        async def mock_create_job(job):
            return job

        async def mock_get_job_by_id(job_id, include_slots=False):
            if job_id == context.job_id:
                if include_slots:
                    context.job.schedule_slots = []
                return context.job
            return None

        async def mock_update_job(job):
            return job

        async def mock_add_schedule_slot(slot):
            return slot

        async def mock_get_slot_by_id(slot_id):
            if slot_id == context.slot_id:
                return ScheduleSlot(
                    id=slot_id,
                    job_id=context.job_id,
                    start_time=context.slot_data["start_time"],
                    end_time=context.slot_data["end_time"],
                    is_proposed_by_cleaner=True,
                    is_accepted=None,
                )
            return None

        # Assign mocks to repository methods
        context.repository.create_job = mock_create_job
        context.repository.get_job_by_id = mock_get_job_by_id
        context.repository.update_job = mock_update_job
        context.repository.add_schedule_slot = mock_add_schedule_slot
        context.repository.get_slot_by_id = mock_get_slot_by_id

    return step


@pytest.mark.asyncio
class TestJobService:
    async def test_create_job_with_valid_data_succeeds(self):
        """Test successful job creation with valid data."""
        with given([prepare_job_service(), prepare_job_data(), prepare_mock_repository()]) as context:
            with when("creating a new job with valid data"):
                from app.api.jobs.models import JobCreate

                job_create = JobCreate(**context.job_data)
                job = await context.job_service.create_job(job_create, context.client_id)

            with then("the job should be created successfully"):
                assert_that(job, not_none())
                assert_that(job.client_id, equal_to(context.client_id))
                assert_that(job.status, equal_to(JobStatus.PENDING))
                assert_that(job.address, equal_to(context.job_data["address"]))
                assert_that(job.estimated_duration_minutes, equal_to(context.job_data["estimated_duration_minutes"]))
                # Assuming base rate is 10 per minute
                expected_cost = context.job_data["estimated_duration_minutes"] * 10.0
                assert_that(job.base_cost, equal_to(expected_cost))

    async def test_get_job_by_id_returns_correct_job(self):
        """Test retrieving a job by ID."""
        with given([prepare_job_service(), prepare_job_data(), prepare_mock_repository()]) as context:
            with when("retrieving a job by its ID"):
                job = await context.job_service.get_job(context.job_id)

            with then("the correct job should be returned"):
                assert_that(job, not_none())
                assert_that(job.id, equal_to(context.job_id))
                assert_that(job.client_id, equal_to(context.client_id))

    async def test_get_job_by_nonexistent_id_raises_404(self):
        """Test retrieving a non-existent job raises 404."""
        with given([prepare_job_service(), prepare_job_data(), prepare_mock_repository()]) as context:
            with pytest.raises(HTTPException) as exc_info:
                with when("retrieving a job with non-existent ID"):
                    non_existent_id = uuid4()
                    await context.job_service.get_job(non_existent_id)

            with then("a 404 exception should be raised"):
                assert_that(exc_info.value.status_code, equal_to(404))
                assert_that(exc_info.value.detail, equal_to("Job not found"))

    async def test_propose_schedule_slot_succeeds(self):
        """Test proposing a schedule slot for a job."""
        with given([prepare_job_service(), prepare_job_data(), prepare_mock_repository()]) as context:
            with when("proposing a valid schedule slot"):
                from app.api.jobs.models import ScheduleSlotCreate

                slot_create = ScheduleSlotCreate(**context.slot_data)
                slot = await context.job_service.propose_schedule_slot(
                    context.job_id, slot_create, proposed_by_cleaner=True
                )

            with then("the slot should be created successfully"):
                assert_that(slot, not_none())
                assert_that(slot.job_id, equal_to(context.job_id))
                assert_that(slot.start_time, equal_to(context.slot_data["start_time"]))
                assert_that(slot.end_time, equal_to(context.slot_data["end_time"]))
                assert_that(slot.is_proposed_by_cleaner, is_(True))

    async def test_propose_schedule_slot_with_past_time_fails(self):
        """Test proposing a slot with past time fails."""
        with given([prepare_job_service(), prepare_job_data(), prepare_mock_repository()]) as context:
            with pytest.raises(HTTPException) as exc_info:
                with when("proposing a slot with past start time"):
                    from app.api.jobs.models import ScheduleSlotCreate

                    past_slot = ScheduleSlotCreate(
                        start_time=datetime.now(timezone.utc) - timedelta(hours=1),
                        end_time=datetime.now(timezone.utc) + timedelta(hours=1),
                    )
                    await context.job_service.propose_schedule_slot(context.job_id, past_slot, proposed_by_cleaner=True)

            with then("an HTTP 400 exception should be raised"):
                assert_that(exc_info.value.status_code, equal_to(400))
                assert_that(exc_info.value.detail, equal_to("Cannot propose a time slot in the past"))

    async def test_accept_schedule_slot_succeeds(self):
        """Test accepting a proposed schedule slot."""
        with given([prepare_job_service(), prepare_job_data(), prepare_mock_repository()]) as context:
            # Prepare a job with a schedule slot
            context.job.schedule_slots = [
                ScheduleSlot(
                    id=context.slot_id,
                    job_id=context.job_id,
                    start_time=context.slot_data["start_time"],
                    end_time=context.slot_data["end_time"],
                    is_proposed_by_cleaner=True,
                    is_accepted=None,
                )
            ]

            # Override get_job_by_id to return job with slots
            async def mock_get_job_with_slots(job_id, include_slots=False):
                if job_id == context.job_id and include_slots:
                    return context.job
                return None

            context.repository.get_job_by_id = mock_get_job_with_slots

            with when("accepting a valid proposed schedule slot"):
                updated_job = await context.job_service.accept_schedule_slot(
                    context.job_id, context.slot_id, context.client_id, context.cleaner_id
                )

            with then("the job status should be updated to scheduled"):
                assert_that(updated_job.status, equal_to(JobStatus.SCHEDULED))
                assert_that(updated_job.cleaner_id, equal_to(context.cleaner_id))
                assert_that(updated_job.scheduled_for, equal_to(context.slot_data["start_time"]))
                assert_that(context.job.schedule_slots[0].is_accepted, is_(True))

    async def test_start_job_succeeds(self):
        """Test starting a job."""
        with given([prepare_job_service(), prepare_job_data(), prepare_mock_repository()]) as context:
            # Prepare a scheduled job with cleaner assigned
            context.job.status = JobStatus.SCHEDULED
            context.job.cleaner_id = context.cleaner_id

            with when("starting a job"):
                updated_job = await context.job_service.start_job(context.job_id, context.cleaner_id)

            with then("the job status should be updated to in progress"):
                assert_that(updated_job.status, equal_to(JobStatus.IN_PROGRESS))
                assert_that(updated_job.started_at, not_none())

    async def test_start_job_with_wrong_cleaner_fails(self):
        """Test starting a job with wrong cleaner fails."""
        with given([prepare_job_service(), prepare_job_data(), prepare_mock_repository()]) as context:
            # Prepare a scheduled job with cleaner assigned
            context.job.status = JobStatus.SCHEDULED
            context.job.cleaner_id = context.cleaner_id

            with pytest.raises(HTTPException) as exc_info:
                with when("attempting to start a job with wrong cleaner ID"):
                    wrong_cleaner_id = uuid4()
                    await context.job_service.start_job(context.job_id, wrong_cleaner_id)

            with then("an authorization error should be raised"):
                assert_that(exc_info.value.status_code, equal_to(403))
                assert_that(exc_info.value.detail, equal_to("Not authorized to start this job"))

    async def test_complete_job_succeeds(self):
        """Test completing a job."""
        with given([prepare_job_service(), prepare_job_data(), prepare_mock_repository()]) as context:
            # Prepare an in-progress job with cleaner assigned
            context.job.status = JobStatus.IN_PROGRESS
            context.job.cleaner_id = context.cleaner_id
            context.job.started_at = datetime.now(timezone.utc) - timedelta(hours=2)

            with when("completing a job"):
                actual_duration = 120  # 2 hours in minutes
                updated_job = await context.job_service.complete_job(
                    context.job_id, context.cleaner_id, actual_duration
                )

            with then("the job status should be updated to completed"):
                assert_that(updated_job.status, equal_to(JobStatus.COMPLETED))
                assert_that(updated_job.completed_at, not_none())
                assert_that(updated_job.actual_duration_minutes, equal_to(actual_duration))
                assert_that(updated_job.final_cost, not_none())

    async def test_mark_job_paid_succeeds(self):
        """Test marking a job as paid."""
        with given([prepare_job_service(), prepare_job_data(), prepare_mock_repository()]) as context:
            # Prepare a completed job
            context.job.status = JobStatus.COMPLETED
            context.job.cleaner_id = context.cleaner_id
            context.job.actual_duration_minutes = 120
            context.job.final_cost = 1200.0

            with when("marking a job as paid"):
                updated_job = await context.job_service.mark_job_paid(context.job_id)

            with then("the job status should be updated to paid"):
                assert_that(updated_job.status, equal_to(JobStatus.PAID))
