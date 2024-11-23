import enum

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    DateTime,
    Enum,
    Float,
    Text,
)
from sqlalchemy.orm import relationship

from app.models.base import Base

# Table names
TABLE_USERS = "users"
TABLE_JOBS = "jobs"
TABLE_JOB_REVIEWS = "job_reviews"


class JobStatus(str, enum.Enum):
    """Job status enumeration"""

    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    """Payment status enumeration"""

    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class Job(Base):
    """Model representing a cleaning service job"""

    __tablename__ = TABLE_JOBS

    # Foreign Keys
    client_id = Column(
        Integer, ForeignKey(f"{TABLE_USERS}.id"), nullable=False
    )
    cleaner_id = Column(
        Integer, ForeignKey(f"{TABLE_USERS}.id"), nullable=True
    )

    # Job Details
    title = Column(String, nullable=False)
    description = Column(Text)
    location = Column(String, nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    duration_hours = Column(Float, nullable=False)
    rate_per_hour = Column(Float, nullable=False)

    # Status and Payment
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    payment_status = Column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False
    )
    total_amount = Column(Float, nullable=False)
    mpesa_reference = Column(String, nullable=True)

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    client = relationship(
        "User", foreign_keys=[client_id], back_populates="client_jobs"
    )
    cleaner = relationship(
        "User", foreign_keys=[cleaner_id], back_populates="cleaner_jobs"
    )
    reviews = relationship(
        "JobReview", back_populates="job", cascade="all, delete-orphan"
    )


class JobReview(Base):
    """Model representing a review for a completed job"""

    __tablename__ = TABLE_JOB_REVIEWS

    # Foreign Keys
    job_id = Column(Integer, ForeignKey(f"{TABLE_JOBS}.id"), nullable=False)
    reviewer_id = Column(
        Integer, ForeignKey(f"{TABLE_USERS}.id"), nullable=False
    )

    # Review Details
    rating = Column(Integer, nullable=False)
    comment = Column(Text)

    # Relationships
    job = relationship("Job", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews")
