from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.job import JobStatus, PaymentStatus


class JobBase(BaseModel):
    """Base Job Schema"""

    title: str = Field(..., min_length=5, max_length=255)
    description: Optional[str] = None
    location: str = Field(..., min_length=5)
    scheduled_at: datetime
    duration_hours: float = Field(..., gt=0)
    rate_per_hour: float = Field(..., gt=0)


class JobCreate(JobBase):
    """Schema for creating a new job"""

    pass


class JobUpdate(BaseModel):
    """Schema for updating a job"""

    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = None
    location: Optional[str] = Field(None, min_length=5)
    scheduled_at: Optional[datetime] = None
    duration_hours: Optional[float] = Field(None, gt=0)
    rate_per_hour: Optional[float] = Field(None, gt=0)


class JobInDBBase(JobBase):
    """Base Job Schema with DB fields"""

    id: int
    client_id: int
    cleaner_id: Optional[int] = None
    status: JobStatus
    payment_status: PaymentStatus
    total_amount: float
    mpesa_reference: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobResponse(JobInDBBase):
    """Schema for job responses"""

    pass


class JobReviewBase(BaseModel):
    """Base Review Schema"""

    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class JobReviewCreate(JobReviewBase):
    """Schema for creating a new review"""

    pass


class JobReviewInDBBase(JobReviewBase):
    """Base Review Schema with DB fields"""

    id: int
    job_id: int
    reviewer_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class JobReviewResponse(JobReviewInDBBase):
    """Schema for review responses"""

    pass
