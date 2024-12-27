from enum import Enum as PyEnum
from typing import Any
from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.api.shared.database import Base, TimestampMixin


class PaymentStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentProvider(str, PyEnum):
    MPESA = "mpesa"


class Payment(Base, TimestampMixin):
    def __init__(self, **kw: Any):
        super().__init__(kw)
        self.completed_at = None

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="KES")
    provider = Column(String, nullable=False)
    status = Column(String, nullable=False, default=PaymentStatus.PENDING)
    reference = Column(String, unique=True, index=True, nullable=False)

    # Provider-specific fields
    provider_reference = Column(String, unique=True, nullable=True)  # e.g., M-PESA transaction ID
    provider_metadata = Column(JSON, nullable=True)  # Additional provider data

    # Relations
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    job = relationship("Job", back_populates="payments")
    user = relationship("User", back_populates="payments")
