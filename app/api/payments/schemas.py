from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

from app.api.payments.models import PaymentProvider, PaymentStatus


class PaymentBase(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = Field(default="KES", min_length=3, max_length=3)
    provider: PaymentProvider = Field(default=PaymentProvider.MPESA)
    job_id: int

    class Config:
        from_attributes = True


class PaymentCreate(PaymentBase):
    pass


class MPESAPaymentCreate(PaymentCreate):
    phone_number: str = Field(..., min_length=10, max_length=12)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """Validate phone number format."""
        if not v.startswith("254"):
            raise ValueError("Phone number must start with 254")
        if not v[3:].isdigit():
            raise ValueError("Invalid phone number format")
        return v


class PaymentResponse(PaymentBase):
    id: int
    status: PaymentStatus
    reference: str
    provider_reference: Optional[str] = None
    provider_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PaymentUpdate(BaseModel):
    provider_reference: Optional[str] = None
    status: Optional[PaymentStatus] = None
    provider_metadata: Optional[Dict[str, Any]] = None
