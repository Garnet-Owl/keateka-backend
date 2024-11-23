from sqlalchemy import Boolean, String, Enum, Float, Integer
from sqlalchemy.orm import relationship, mapped_column, Mapped
import enum
from typing import Optional
from app.models.base import Base


class UserType(str, enum.Enum):
    CLIENT = "client"
    CLEANER = "cleaner"
    ADMIN = "admin"


class User(Base):
    """
    User Model representing clients, cleaners and admins in the system
    """

    __tablename__ = "users"

    # Basic Info
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    # User Type and Status
    user_type: Mapped[UserType] = mapped_column(Enum(UserType), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Cleaner Specific Fields
    hourly_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    average_rating: Mapped[float] = mapped_column(Float, default=0.0)
    total_jobs: Mapped[int] = mapped_column(Integer, default=0)
    completed_jobs: Mapped[int] = mapped_column(Integer, default=0)

    # Firebase Cloud Messaging token for notifications
    fcm_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    client_jobs = relationship(
        "Job", foreign_keys="Job.client_id", back_populates="client", lazy="dynamic"
    )

    cleaner_jobs = relationship(
        "Job", foreign_keys="Job.cleaner_id", back_populates="cleaner", lazy="dynamic"
    )

    reviews = relationship(
        "JobReview", foreign_keys="JobReview.reviewer_id", back_populates="reviewer"
    )
