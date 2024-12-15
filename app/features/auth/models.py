from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.shared.database import Base, TimestampMixin


class UserRole(str, PyEnum):
    CLIENT = "client"
    CLEANER = "cleaner"
    ADMIN = "admin"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    firebase_uid = Column(String, unique=True, nullable=True)
    email = Column(String, unique=True, index=True)
    phone_number = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True)  # Null for Firebase users
    role = Column(String, default=UserRole.CLIENT)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Profile fields
    full_name = Column(String)
    profile_photo = Column(String, nullable=True)

    # Timestamps
    last_login = Column(DateTime, nullable=True)

    # Relationships
    client_jobs = relationship(
        "Job",
        foreign_keys="[Job.client_id]",
        back_populates="client",
        lazy="dynamic",
    )
    cleaner_jobs = relationship(
        "Job",
        foreign_keys="[Job.cleaner_id]",
        back_populates="cleaner",
        lazy="dynamic",
    )
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    is_revoked = Column(Boolean, default=False)

    # Relationship
    user = relationship("User", back_populates="refresh_tokens")
