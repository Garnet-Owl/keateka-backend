from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator
from app.models.user import UserType


class UserBase(BaseModel):
    """Base User Schema"""

    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    phone_number: str = Field(..., pattern=r"^\+?\d{10,15}$")
    user_type: UserType


class UserCreate(UserBase):
    """Schema for creating a new user"""

    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @validator("confirm_password")
    def passwords_match(cls, v, values, **kwargs):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v


class UserUpdate(BaseModel):
    """Schema for updating a user"""

    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone_number: Optional[str] = Field(None, pattern=r"^\+?\d{10,15}$")
    hourly_rate: Optional[float] = Field(None, ge=0)
    bio: Optional[str] = Field(None, max_length=500)
    fcm_token: Optional[str] = None
    is_active: Optional[bool] = None


class UserInDBBase(UserBase):
    """Base User Schema with DB fields"""

    id: int
    is_active: bool = True
    is_verified: bool = False
    hourly_rate: Optional[float] = None
    bio: Optional[str] = None
    average_rating: float = 0.0
    total_jobs: int = 0
    completed_jobs: int = 0
    fcm_token: Optional[str] = None

    class Config:
        from_attributes = True


class UserResponse(UserInDBBase):
    """Schema for user responses"""

    pass


class UserInDB(UserInDBBase):
    """Schema for user in DB"""

    hashed_password: str
