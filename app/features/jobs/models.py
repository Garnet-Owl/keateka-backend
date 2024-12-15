from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from app.shared.database import Base


class JobStatus(str, PyEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cleaner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, default=JobStatus.PENDING)

    # Location details
    location = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Time tracking
    scheduled_time = Column(DateTime, nullable=False)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    estimated_duration = Column(Integer, nullable=False)  # in minutes
    actual_duration = Column(Integer, nullable=True)

    # Cost details
    base_rate = Column(Float, nullable=False)
    final_amount = Column(Float, nullable=True)

    # Relationships
    client = relationship("User", foreign_keys=[client_id], back_populates="client_jobs")
    cleaner = relationship("User", foreign_keys=[cleaner_id], back_populates="cleaner_jobs")
    reviews = relationship("Review", back_populates="job")
