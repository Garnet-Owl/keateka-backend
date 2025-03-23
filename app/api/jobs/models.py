from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Enum as SQLAEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.api.storage.base import Base


# Database Models
class JobStatus(str, Enum):
    PENDING = "pending"  # Job created but no cleaner assigned
    SCHEDULED = "scheduled"  # Cleaner assigned and time slot confirmed
    IN_PROGRESS = "in_progress"  # Cleaner has started the job
    COMPLETED = "completed"  # Job finished but not paid
    PAID = "paid"  # Job completed and payment received
    CANCELED = "canceled"  # Job canceled by either party


class Job(Base):
    __tablename__ = "jobs"

    id = Column(PGUUID, primary_key=True, default=uuid4)
    client_id = Column(PGUUID, ForeignKey("users.id"), nullable=False)
    cleaner_id = Column(PGUUID, ForeignKey("users.id"), nullable=True)  # Nullable until assigned

    status = Column(SQLAEnum(JobStatus), default=JobStatus.PENDING, nullable=False)

    # Location details
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Job details
    description = Column(Text, nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=False)
    actual_duration_minutes = Column(Integer, nullable=True)

    # Cost information
    base_cost = Column(Float, nullable=False)
    final_cost = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    scheduled_for = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    client = relationship("User", foreign_keys=[client_id], back_populates="client_jobs")
    cleaner = relationship("User", foreign_keys=[cleaner_id], back_populates="cleaner_jobs")
    schedule_slots = relationship("ScheduleSlot", back_populates="job", cascade="all, delete-orphan")


class ScheduleSlot(Base):
    __tablename__ = "schedule_slots"

    id = Column(PGUUID, primary_key=True, default=uuid4)
    job_id = Column(PGUUID, ForeignKey("jobs.id"), nullable=False)

    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    is_proposed_by_cleaner = Column(Integer, default=False, nullable=False)
    is_accepted = Column(Integer, nullable=True)  # Null=pending, True=accepted, False=rejected

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    job = relationship("Job", back_populates="schedule_slots")


# Pydantic Schemas
class LocationInfo(BaseModel):
    address: str
    city: str
    latitude: float
    longitude: float


class ScheduleSlotCreate(BaseModel):
    start_time: datetime
    end_time: datetime


class ScheduleSlotResponse(ScheduleSlotCreate):
    id: UUID
    job_id: UUID
    is_proposed_by_cleaner: bool
    is_accepted: Optional[bool] = None
    created_at: datetime

    class Config:
        from_attributes = True


class JobCreate(BaseModel):
    address: str
    city: str
    latitude: float
    longitude: float
    description: Optional[str] = None
    estimated_duration_minutes: int = Field(..., gt=0)


class JobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    description: Optional[str] = None
    actual_duration_minutes: Optional[int] = None
    final_cost: Optional[float] = None


class JobResponse(BaseModel):
    id: UUID
    client_id: UUID
    cleaner_id: Optional[UUID] = None
    status: JobStatus
    address: str
    city: str
    latitude: float
    longitude: float
    description: Optional[str] = None
    estimated_duration_minutes: int
    actual_duration_minutes: Optional[int] = None
    base_cost: float
    final_cost: Optional[float] = None
    created_at: datetime
    scheduled_for: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    schedule_slots: Optional[List[ScheduleSlotResponse]] = None

    class Config:
        from_attributes = True


class ScheduleJobRequest(BaseModel):
    job_id: UUID
    slot_id: UUID


class JobStartRequest(BaseModel):
    job_id: UUID


class JobCompleteRequest(BaseModel):
    job_id: UUID
    actual_duration_minutes: int
