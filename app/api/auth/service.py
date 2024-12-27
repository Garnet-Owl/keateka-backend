from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import models, schemas, security
from app.api.auth.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.api.shared.config import settings
from app.api.shared.utils.cache import CacheManager


class AuthService:
    def __init__(self, db: AsyncSession, cache_manager: Optional[CacheManager] = None):
        self.db = db
        self.cache = cache_manager

    async def create_user(self, user_data: schemas.UserCreate, is_firebase_user: bool = False) -> models.User:
        """Create a new user."""
        # Check if email already exists
        if await self.get_user_by_email(str(user_data.email)):
            raise UserAlreadyExistsError(str(user_data.email))

        # Create new user
        user = models.User(**user_data.model_dump(exclude={"password"}))
        if not is_firebase_user:
            user.hashed_password = security.get_password_hash(user_data.password)

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate_user(self, email: str, password: str) -> models.User:
        """Authenticate user with email and password."""
        user = await self.get_user_by_email(str(email))

        if not user or not security.verify_password(password, user.hashed_password):
            raise InvalidCredentialsError

        if not user.is_active:
            raise InactiveUserError

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await self.db.commit()

        return user

    async def authenticate_firebase_user(self, firebase_token: str) -> Tuple[models.User, bool]:
        """Authenticate or create user with Firebase token."""
        try:
            firebase_data = await security.verify_firebase_token(firebase_token)
            user = await self.get_user_by_firebase_uid(firebase_data["uid"])

            is_new_user = False
            if not user:
                # Create new user from Firebase data
                user_data = schemas.UserCreate(
                    email=firebase_data["email"],
                    firebase_uid=firebase_data["uid"],
                    full_name=firebase_data.get("name", ""),
                    phone_number=firebase_data.get("phone_number", ""),
                )
                user = await self.create_user(user_data, is_firebase_user=True)
                is_new_user = True

            # Update last login
            user.last_login = datetime.now(timezone.utc)
            await self.db.commit()

            return user, is_new_user
        except Exception as e:
            msg = f"Firebase authentication failed: {e!s}"
            raise InvalidCredentialsError(msg)

    async def create_tokens(self, user: models.User) -> Dict:
        """Create access and refresh tokens."""
        # Create access token
        access_token_data = security.create_access_token(
            subject=user.id, role=user.role, firebase_uid=user.firebase_uid
        )

        # Create refresh token
        refresh_token_data = security.create_refresh_token(subject=user.id, role=user.role)

        # Store refresh token
        refresh_token = models.RefreshToken(
            token=refresh_token_data["token"],
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.db.add(refresh_token)
        await self.db.commit()

        return {
            "access_token": access_token_data["token"],
            "refresh_token": refresh_token_data["token"],
            "token_type": "bearer",
            "expires_in": access_token_data["expires_in"],
        }

    async def refresh_tokens(self, refresh_token: str) -> Dict:
        """Refresh access token using refresh token."""
        try:
            # Verify and decode refresh token
            payload = security.decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise InvalidTokenError("Invalid token type")

            # Get stored refresh token
            token_model = await self.get_refresh_token(refresh_token)
            if not token_model or token_model.is_revoked:
                raise InvalidTokenError("Invalid or revoked refresh token")

            # Check expiration
            if token_model.expires_at < datetime.now(timezone.utc):
                raise InvalidTokenError("Refresh token has expired")

            # Get user
            user = await self.get_user_by_id(int(payload["sub"]))
            if not user or not user.is_active:
                raise InvalidTokenError("User is inactive or not found")

            # Revoke old refresh token
            token_model.is_revoked = True
            await self.db.commit()

            # Create new tokens
            return await self.create_tokens(user)

        except Exception as e:
            raise InvalidTokenError(str(e))

    async def invalidate_token(self, token: str) -> None:
        """Invalidate a token (add to blacklist)."""
        if self.cache:
            key = f"blacklist:{token}"
            await self.cache.set(key, "1", expires_in=timedelta(days=7))

    async def is_token_blacklisted(self, token: str) -> bool:
        """Check if a token is blacklisted."""
        if self.cache:
            key = f"blacklist:{token}"
            return await self.cache.exists(key)
        return False

    async def get_user_by_id(self, user_id: int) -> Optional[models.User]:
        """Get user by ID."""
        result = await self.db.execute(select(models.User).filter(models.User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[models.User]:
        """Get user by email."""
        result = await self.db.execute(select(models.User).filter(models.User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[models.User]:
        """Get user by Firebase UID."""
        result = await self.db.execute(select(models.User).filter(models.User.firebase_uid == firebase_uid))
        return result.scalar_one_or_none()

    async def get_refresh_token(self, token: str) -> Optional[models.RefreshToken]:
        """Get refresh token from database."""
        result = await self.db.execute(
            select(models.RefreshToken).filter(
                models.RefreshToken.token == token,
                models.RefreshToken.is_revoked is False,
            )
        )
        return result.scalar_one_or_none()

    async def update_user(self, user_id: int, user_data: schemas.UserUpdate) -> models.User:
        """Update user details."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError(str(user_id))

        for field, value in user_data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)

        await self.db.commit()
        await self.db.refresh(user)
        return user
