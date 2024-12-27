from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
from app.api.jobs.models import JobStatus
from datetime import UTC


class LocationBase(BaseModel):
    """Base schema for location details."""

    location: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class JobBase(LocationBase):
    """Base schema for job details."""

    scheduled_time: datetime
    estimated_duration: int = Field(..., ge=60, description="Duration in minutes")
    base_rate: float = Field(..., ge=0)


class JobCreate(JobBase):
    """Schema for creating a new job."""

    @validator("scheduled_time")
    def validate_scheduled_time(cls, v):
        if v < datetime.now(UTC):
            raise ValueError("Cannot schedule job in the past")
        return v


class JobUpdate(BaseModel):
    """Schema for updating a job."""

    cleaner_id: Optional[int] = None
    status: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    actual_duration: Optional[int] = None
    final_amount: Optional[float] = None

    @validator("status")
    def validate_status(cls, v):
        if v and v not in JobStatus.__members__:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(JobStatus.__members__)}")
        return v


class JobResponse(JobBase):
    """Schema for job response."""

    id: int
    client_id: int
    cleaner_id: Optional[int]
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    actual_duration: Optional[int]
    final_amount: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class TrackingPauseRequest(BaseModel):
    """Schema for pausing job tracking."""

    reason: str = Field(..., min_length=1, max_length=500)


class TrackingStatus(BaseModel):
    """Schema for tracking status response."""

    status: str
    current_duration: int
    start_time: str
    paused_duration: int
    is_overtime: bool
    overtime_minutes: int
    estimated_completion: datetime


class TrackingSummary(BaseModel):
    """Schema for tracking summary response."""

    start_time: datetime
    end_time: datetime
    actual_duration: int
    paused_duration: int
    final_amount: float
