from datetime import timedelta
from typing import Any, Dict
from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select
from jose import JWTError

from app.core import security
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserResponse
from app.models.user import User, UserType
from app.database import get_db

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
) -> Any:
    """
    Register new user.
    """
    stmt = select(User).where(User.email == user_in.email)
    existing_user = await db.execute(stmt).scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user object explicitly converting types
    user = User(
        email=str(user_in.email),  # Convert EmailStr to str
        hashed_password=get_password_hash(user_in.password),
        full_name=str(user_in.full_name),
        phone_number=str(user_in.phone_number),
        user_type=UserType(
            user_in.user_type
        ),  # Explicitly convert to UserType enum
        is_active=True,
        is_verified=False,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login.
    """
    stmt = select(User).where(User.email == form_data.username)
    user = db.execute(stmt).scalar_one_or_none()

    if not user or not verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "refresh_token": security.create_refresh_token(user.id),
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
def refresh_token(
    *,
    db: Session = Depends(get_db),
    refresh_token: str = Body(..., embed=True),
) -> Dict[str, str]:
    """
    Get new access token using refresh token.
    """
    try:
        payload = security.decode_refresh_token(refresh_token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        stmt = select(User).where(User.id == user_id, User.is_active.is_(True))
        user = db.execute(stmt).scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        access_token_expires = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        return {
            "access_token": security.create_access_token(
                user.id, expires_delta=access_token_expires
            ),
            "token_type": "bearer",
        }

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )


@router.post("/verify-email/{token}")
def verify_email(
    token: str,
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """
    Verify email address.
    """
    try:
        payload = security.decode_verification_token(token)
        stmt = select(User).where(
            User.id == payload["sub"], User.is_verified.is_(False)
        )
        user = db.execute(stmt).scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or already verified",
            )

        user.is_verified = True
        db.commit()
        return {"message": "Email verified successfully"}

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )


@router.post("/forgot-password/{email}")
def forgot_password(
    email: str,
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """
    Password recovery email.
    """
    stmt = select(User).where(User.email == email, User.is_active.is_(True))
    user = db.execute(stmt).scalar_one_or_none()

    if user:
        # Send password reset email
        # This would typically integrate with your email service
        pass
    return {
        "message": "If email exists, password reset instructions have been sent"
    }
