from datetime import timedelta
from typing import List, Optional, Tuple, Sequence

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import true

from app.core.notifications import send_notification
from app.models.job import Job, JobStatus
from app.models.user import User, UserType


class JobMatchingService:
    def __init__(self, db: Optional[Session] = None):
        self.db: Optional[Session] = db

    @staticmethod
    def _calculate_match_score(job: Job, cleaner: User) -> float:
        """
        Calculate a match score between 0 and 1 for a job-cleaner pair.
        Higher score indicates better match.
        """
        # Base score starts at 1.0
        score = 1.0

        # Rating factor (0.3 weight)
        if cleaner.average_rating:
            rating_score = min(float(cleaner.average_rating) / 5.0, 1.0)
            score *= 0.7 + (rating_score * 0.3)

        # Experience factor based on completed jobs (0.2 weight)
        if cleaner.completed_jobs:
            experience_score = min(float(cleaner.completed_jobs) / 100.0, 1.0)
            score *= 0.8 + (experience_score * 0.2)

        # Price match factor (0.2 weight)
        if cleaner.hourly_rate:
            price_diff = abs(
                float(job.rate_per_hour) - float(cleaner.hourly_rate)
            )
            price_score = max(
                1.0 - (price_diff / float(job.rate_per_hour)), 0.0
            )
            score *= 0.8 + (price_score * 0.2)

        # Success rate factor (0.3 weight)
        if cleaner.total_jobs > 0:
            success_rate = float(cleaner.completed_jobs) / float(
                cleaner.total_jobs
            )
            score *= 0.7 + (success_rate * 0.3)

        return score

    @staticmethod
    def _notify_cleaner_of_match(
        cleaner: User, job: Job, score: float
    ) -> None:
        """Send notification to cleaner about a potential job match."""
        if score >= 0.8:  # Only notify for high-quality matches
            send_notification(
                user_id=cleaner.id,
                title="New Job Match",
                body=f"New cleaning job available in {job.location}",
                data={
                    "job_id": str(job.id),
                    "match_score": str(round(score * 100, 1)) + "%",
                    "rate": str(job.rate_per_hour),
                    "scheduled_at": job.scheduled_at.isoformat(),
                },
            )

    @staticmethod
    def _has_time_conflict(job: Job, busy_times: Sequence[Job]) -> bool:
        """Check if a job conflicts with any of the busy time slots."""
        job_start = job.scheduled_at
        job_end = job.scheduled_at + timedelta(hours=float(job.duration_hours))

        for busy in busy_times:
            busy_start = busy.scheduled_at
            busy_end = busy.scheduled_at + timedelta(
                hours=float(busy.duration_hours)
            )

            if job_start <= busy_end and job_end >= busy_start:
                return True

        return False

    def find_matches_for_job(
        self, job_id: int, max_matches: int = 5
    ) -> List[Tuple[User, float]]:
        """
        Find suitable cleaners for a job based on various criteria:
        - Location proximity
        - Availability
        - Rating
        - Price range
        """
        if not self.db:
            return []

        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job or job.status != JobStatus.PENDING:
            return []

        # Base query for available cleaners
        query = self.db.query(User).filter(
            User.user_type == UserType.CLEANER,
            User.is_active.is_(true()),
            User.is_verified.is_(true()),
        )

        # Filter by hourly rate (within 20% of job rate)
        min_rate = float(job.rate_per_hour) * 0.8
        max_rate = float(job.rate_per_hour) * 1.2
        query = query.filter(
            User.hourly_rate >= min_rate, User.hourly_rate <= max_rate
        )

        # Check cleaner availability
        job_start = job.scheduled_at
        job_end = job.scheduled_at + timedelta(hours=float(job.duration_hours))

        # Exclude cleaners who have overlapping jobs
        busy_cleaners = (
            self.db.query(Job.cleaner_id)
            .filter(
                Job.status.in_([JobStatus.ACCEPTED, JobStatus.IN_PROGRESS]),
                Job.cleaner_id.isnot(None),
                or_(
                    and_(
                        Job.scheduled_at <= job_start,
                        Job.scheduled_at
                        + timedelta(hours=float(Job.duration_hours))
                        >= job_start,
                    ),
                    and_(
                        Job.scheduled_at <= job_end,
                        Job.scheduled_at
                        + timedelta(hours=float(Job.duration_hours))
                        >= job_end,
                    ),
                ),
            )
            .distinct()
        )

        query = query.filter(User.id.notin_(busy_cleaners))

        # Order by rating and completed jobs
        query = query.order_by(
            User.average_rating.desc(), User.completed_jobs.desc()
        )

        # Get top matches
        potential_matches = query.limit(max_matches).all()

        # Calculate match scores and return results
        matches = []
        for cleaner in potential_matches:
            score = self._calculate_match_score(job, cleaner)
            matches.append((cleaner, score))
            self._notify_cleaner_of_match(cleaner, job, score)

        # Sort by match score
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def suggest_jobs_for_cleaner(
        self, cleaner_id: int, max_suggestions: int = 5
    ) -> List[Tuple[Job, float]]:
        """Find suitable jobs for a cleaner based on their profile."""
        if not self.db:
            return []

        cleaner = (
            self.db.query(User)
            .filter(
                User.id == cleaner_id,
                User.user_type == UserType.CLEANER,
                User.is_active.is_(true()),
            )
            .first()
        )

        if not cleaner:
            return []

        # Get pending jobs
        min_rate = float(cleaner.hourly_rate) * 0.8
        max_rate = float(cleaner.hourly_rate) * 1.2

        query = self.db.query(Job).filter(
            Job.status == JobStatus.PENDING,
            Job.rate_per_hour >= min_rate,
            Job.rate_per_hour <= max_rate,
        )

        # Check availability
        busy_times = (
            self.db.query(Job)
            .filter(
                Job.cleaner_id == cleaner_id,
                Job.status.in_([JobStatus.ACCEPTED, JobStatus.IN_PROGRESS]),
            )
            .all()
        )

        # Filter out jobs that overlap with existing commitments
        available_jobs = []
        for job in query.all():
            if not self._has_time_conflict(job, busy_times):
                score = self._calculate_match_score(job, cleaner)
                available_jobs.append((job, score))

        # Sort by match score and return top suggestions
        available_jobs.sort(key=lambda x: x[1], reverse=True)
        return available_jobs[:max_suggestions]


# Create singleton instance
matching_service = (
    JobMatchingService()
)  # DB will be set during request lifecycle
