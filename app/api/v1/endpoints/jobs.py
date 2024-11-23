from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Optional
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
from sqlalchemy.orm import relationship, Mapped
import enum

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User

# Table name constants
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
    """Job model representing cleaning service jobs"""

    __tablename__ = TABLE_JOBS

    # Foreign Keys
    client_id: Mapped[int] = Column(
        Integer, ForeignKey(f"{TABLE_USERS}.id"), nullable=False
    )
    cleaner_id: Mapped[Optional[int]] = Column(
        Integer, ForeignKey(f"{TABLE_USERS}.id"), nullable=True
    )

    # Job Details
    title: Mapped[str] = Column(String, nullable=False)
    description: Mapped[Optional[str]] = Column(Text)
    location: Mapped[str] = Column(String, nullable=False)
    scheduled_at: Mapped[datetime] = Column(
        DateTime(timezone=True), nullable=False
    )
    duration_hours: Mapped[float] = Column(Float, nullable=False)
    rate_per_hour: Mapped[float] = Column(Float, nullable=False)

    # Status and Payment
    status: Mapped[JobStatus] = Column(
        Enum(JobStatus), default=JobStatus.PENDING, nullable=False
    )
    payment_status: Mapped[PaymentStatus] = Column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False
    )
    total_amount: Mapped[float] = Column(Float, nullable=False)
    mpesa_reference: Mapped[Optional[str]] = Column(String, nullable=True)

    # Timestamps
    started_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    client: Mapped[User] = relationship(
        "User", foreign_keys=[client_id], back_populates="client_jobs"
    )
    cleaner: Mapped[Optional[User]] = relationship(
        "User", foreign_keys=[cleaner_id], back_populates="cleaner_jobs"
    )
    reviews: Mapped[list[JobReview]] = relationship(
        "JobReview", back_populates="job", cascade="all, delete-orphan"
    )


class JobReview(Base):
    """Review model for job reviews"""

    __tablename__ = TABLE_JOB_REVIEWS

    # Foreign Keys
    job_id: Mapped[int] = Column(
        Integer, ForeignKey(f"{TABLE_JOBS}.id"), nullable=False
    )
    reviewer_id: Mapped[int] = Column(
        Integer, ForeignKey(f"{TABLE_USERS}.id"), nullable=False
    )

    # Review Details
    rating: Mapped[int] = Column(Integer, nullable=False)
    comment: Mapped[Optional[str]] = Column(Text)

    # Relationships
    job: Mapped[Job] = relationship("Job", back_populates="reviews")
    reviewer: Mapped[User] = relationship(
        "User", back_populates="reviews_given"
    )
