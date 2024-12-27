from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.api.auth.models import UserRole


def validate_password_strength(password: str) -> str:
    """
    Validate password strength requirements.

    Args:
        password: The password to validate

    Returns:
        The validated password

    Raises:
        ValueError: If password doesn't meet strength requirements
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not any(char.isdigit() for char in password):
        raise ValueError("Password must contain at least one number")
    if not any(char.isupper() for char in password):
        raise ValueError("Password must contain at least one uppercase letter")
    return password


class UserBase(BaseModel):
    """Base schema for user details."""

    email: EmailStr
    phone_number: str = Field(..., pattern=r"^\+?1?\d{9,15}$")
    full_name: str = Field(..., min_length=2, max_length=100)
    role: UserRole = Field(default=UserRole.CLIENT)

    @classmethod
    @field_validator("phone_number")
    def validate_phone(cls, v: str) -> str:
        if not v.replace("+", "").isdigit():
            raise ValueError("Phone number must contain only digits and + symbol")
        return v


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=8)
    firebase_uid: Optional[str] = None

    @classmethod
    @field_validator("password")
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserUpdate(BaseModel):
    """Schema for updating user details."""

    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone_number: Optional[str] = None
    profile_photo: Optional[str] = None
    is_active: Optional[bool] = None

    @classmethod
    @field_validator("phone_number")
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.replace("+", "").isdigit():
            raise ValueError("Phone number must contain only digits and + symbol")
        return v


class UserResponse(UserBase):
    """Schema for user response."""

    id: int
    is_active: bool
    is_verified: bool
    profile_photo: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for authentication tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """Schema for token payload."""

    sub: str
    exp: datetime
    type: str
    role: UserRole


class LoginRequest(BaseModel):
    """Schema for login request."""

    email: EmailStr
    password: str = Field(..., min_length=8)


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""

    refresh_token: str


class FirebaseLoginRequest(BaseModel):
    """Schema for Firebase login request."""

    firebase_token: str


class PasswordReset(BaseModel):
    """Schema for password reset."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str
    new_password: str = Field(..., min_length=8)

    @classmethod
    @field_validator("new_password")
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


class MessageResponse(BaseModel):
    """Schema for simple message responses."""

    message: str
