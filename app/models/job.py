from typing import TYPE_CHECKING
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Enum, Float, Text
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base

if TYPE_CHECKING:
    pass


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class Job(Base):
    __tablename__ = "jobs"

    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cleaner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    title = Column(String, nullable=False)
    description = Column(Text)
    location = Column(String, nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    duration_hours = Column(Float, nullable=False)
    rate_per_hour = Column(Float, nullable=False)

    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)

    total_amount = Column(Float, nullable=False)
    mpesa_reference = Column(String, nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    client = relationship(
        "User", foreign_keys=[client_id], back_populates="client_jobs"
    )
    cleaner = relationship(
        "User", foreign_keys=[cleaner_id], back_populates="cleaner_jobs"
    )
    reviews = relationship("JobReview", back_populates="job")


class JobReview(Base):
    __tablename__ = "job_reviews"

    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)

    job = relationship("Job", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews")
