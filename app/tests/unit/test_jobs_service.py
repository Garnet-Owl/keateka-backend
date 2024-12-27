# tests/unit/test_jobs_service.py

from datetime import datetime, UTC
import pytest
from unittest.mock import Mock
from sqlalchemy.orm import Session
from app.api.jobs import models, schemas, service
from app.api.shared.exceptions import (
    NotFoundException,
    ValidationError,
)  # Added ValidationError
from app.tests.givenpy import given, when, then


def prepare_db():
    def step(context):
        context.db = Mock(spec=Session)
        context.db.query = Mock(return_value=context.db)
        context.db.filter = Mock(return_value=context.db)
        context.db.first = Mock(return_value=None)
        context.db.all = Mock(return_value=[])
        context.db.commit = Mock()
        context.db.refresh = Mock()
        context.db.add = Mock()
        context.db.delete = Mock()  # Added missing delete mock

    return step


def prepare_test_job():
    def step(context):
        context.test_job_data = schemas.JobCreate(
            client_id=1,
            location="Test Location",
            latitude=-1.2921,
            longitude=36.8219,
            scheduled_time=datetime.now(UTC),
            estimated_duration=120,  # 2 hours
            base_rate=1000.0,
        )

    return step


class TestJobService:
    def test_create_job_with_valid_data_succeeds(self):
        """Test successful job creation with valid data."""
        with given([prepare_db(), prepare_test_job()]) as context:
            job_service = service.JobService(context.db)

            with when("creating a new job with valid data"):
                job = job_service.create_job(context.test_job_data)

            with then("job should be created successfully"):
                assert job is not None
                assert job.client_id == context.test_job_data.client_id
                assert job.location == context.test_job_data.location
                assert job.status == models.JobStatus.PENDING
                context.db.add.assert_called_once()
                context.db.commit.assert_called_once()

    def test_get_job_with_valid_id_returns_job(self):
        """Test retrieving a job with valid ID."""
        with given([prepare_db(), prepare_test_job()]) as context:
            job_service = service.JobService(context.db)
            job = models.Job(
                id=1,
                client_id=context.test_job_data.client_id,
                location=context.test_job_data.location,
                status=models.JobStatus.PENDING,
            )
            context.db.query().filter().first.return_value = job

            with when("getting a job with valid ID"):
                retrieved_job = job_service.get_job(1)

            with then("should return the job"):
                assert retrieved_job is not None
                assert retrieved_job.id == 1
                assert retrieved_job.client_id == context.test_job_data.client_id

    def test_delete_nonexistent_job_raises_error(self):
        """Test deleting a nonexistent job fails."""
        with given([prepare_db()]) as context:
            job_service = service.JobService(context.db)
            context.db.query().filter().first.return_value = None

            with (
                when("deleting a nonexistent job"),
                pytest.raises(NotFoundException) as exc_info,
            ):
                job_service.delete_job(999)

            with then("should raise not found error"):
                assert "Job with id 999 not found" in str(exc_info.value)

    def test_job_status_transitions(self):
        """Test job status transitions follow correct flow."""
        with given([prepare_db(), prepare_test_job()]) as context:
            job_service = service.JobService(context.db)
            job = models.Job(
                id=1,
                client_id=context.test_job_data.client_id,
                location=context.test_job_data.location,
                status=models.JobStatus.PENDING,
            )
            context.db.query().filter().first.return_value = job

            # Test valid status transitions
            status_transitions = [
                models.JobStatus.ACCEPTED,
                models.JobStatus.IN_PROGRESS,
                models.JobStatus.COMPLETED,
            ]

            for new_status in status_transitions:
                with when(f"updating job status to {new_status}"):
                    update_data = schemas.JobUpdate(status=new_status)
                    updated_job = job_service.update_job(1, update_data)

                with then(f"status should be updated to {new_status}"):
                    assert updated_job.status == new_status

    def test_job_with_invalid_coordinates_fails(self):
        """Test job creation with invalid coordinates fails."""
        with given([prepare_db()]) as context:
            job_service = service.JobService(context.db)
            invalid_job_data = schemas.JobCreate(
                client_id=1,
                location="Invalid Location",
                latitude=91.0,  # Invalid latitude (>90)
                longitude=180.0,
                scheduled_time=datetime.now(UTC),
                estimated_duration=120,
                base_rate=1000.0,
            )

            with (
                when("creating a job with invalid coordinates"),
                pytest.raises(ValidationError) as exc_info,
            ):
                job_service.create_job(invalid_job_data)

            with then("should raise validation error"):
                assert "Invalid coordinates" in str(exc_info.value)

    def test_update_job_final_amount_calculation(self):
        """Test job final amount is calculated correctly on completion."""
        with given([prepare_db(), prepare_test_job()]) as context:
            job_service = service.JobService(context.db)
            job = models.Job(
                id=1,
                client_id=context.test_job_data.client_id,
                location=context.test_job_data.location,
                status=models.JobStatus.IN_PROGRESS,
                base_rate=1000.0,  # 1000 per hour
                start_time=datetime(2024, 1, 1, 10, 0),  # 10:00 AM
            )
            context.db.query().filter().first.return_value = job

            update_data = schemas.JobUpdate(
                status=models.JobStatus.COMPLETED,
                end_time=datetime(2024, 1, 1, 12, 30),  # 12:30 PM (2.5 hours)
                actual_duration=150,  # 150 minutes
            )

            with when("completing a job"):
                completed_job = job_service.update_job(1, update_data)

            with then("final amount should be calculated correctly"):
                expected_amount = (150 / 60) * 1000  # 2.5 hours * 1000
                assert completed_job.final_amount == expected_amount
                assert completed_job.status == models.JobStatus.COMPLETED

    def test_get_jobs_by_client_returns_client_jobs(self):
        """Test retrieving all jobs for a specific client."""
        with given([prepare_db(), prepare_test_job()]) as context:
            job_service = service.JobService(context.db)
            client_jobs = [
                models.Job(id=1, client_id=1, status=models.JobStatus.PENDING),
                models.Job(id=2, client_id=1, status=models.JobStatus.COMPLETED),
            ]
            context.db.query().filter().all.return_value = client_jobs

            with when("getting jobs for a specific client"):
                jobs = job_service.get_jobs_by_client(1)

            with then("should return list of client's jobs"):
                assert len(jobs) == 2
                assert all(job.client_id == 1 for job in jobs)

    def test_get_jobs_by_cleaner_returns_cleaner_jobs(self):
        """Test retrieving all jobs for a specific cleaner."""
        with given([prepare_db(), prepare_test_job()]) as context:
            job_service = service.JobService(context.db)
            cleaner_jobs = [
                models.Job(id=1, cleaner_id=1, status=models.JobStatus.IN_PROGRESS),
                models.Job(id=2, cleaner_id=1, status=models.JobStatus.COMPLETED),
            ]
            context.db.query().filter().all.return_value = cleaner_jobs

            with when("getting jobs for a specific cleaner"):
                jobs = job_service.get_jobs_by_cleaner(1)

            with then("should return list of cleaner's jobs"):
                assert len(jobs) == 2
                assert all(job.cleaner_id == 1 for job in jobs)

    def test_delete_job_with_valid_id_succeeds(self):
        """Test successful job deletion."""
        with given([prepare_db(), prepare_test_job()]) as context:
            job_service = service.JobService(context.db)
            existing_job = models.Job(
                id=1,
                client_id=context.test_job_data.client_id,
                location=context.test_job_data.location,
                status=models.JobStatus.PENDING,
            )
            context.db.query().filter().first.return_value = existing_job

            with when("deleting a job"):
                job_service.delete_job(1)

            with then("job should be deleted"):
                context.db.delete.assert_called_once_with(existing_job)
                context.db.commit.assert_called_once()
