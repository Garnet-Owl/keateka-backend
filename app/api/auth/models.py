from enum import Enum
from uuid import uuid4

from sqlalchemy import Column, Enum as SQLAEnum, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.api.storage.base import Base


class UserRole(str, Enum):
    """User roles in the system."""

    CLIENT = "client"
    CLEANER = "cleaner"
    ADMIN = "admin"


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id = Column(PGUUID, primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLAEnum(UserRole), nullable=False, default=UserRole.CLIENT)
    phone_number = Column(String(20), nullable=True)
    full_name = Column(String(255), nullable=False)

    # Relationships to be added in related models to prevent circular imports
    # client_jobs - defined in Job model
    # cleaner_jobs - defined in Job model
