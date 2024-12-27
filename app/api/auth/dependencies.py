from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import models, security, service
from app.api.auth.exceptions import (
    AuthenticationError,
    InactiveUserError,
    InvalidTokenError,
)
from app.api.shared.database import get_db
from app.api.shared.utils.cache import CacheManager, get_redis_client

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_auth_service(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
) -> service.AuthService:
    """Get AuthService instance with cache manager."""
    cache_manager = CacheManager(redis, prefix="auth")
    return service.AuthService(db, cache_manager)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> models.User:
    """Get current authenticated user."""
    auth_service: service.AuthService = Depends(get_auth_service)
    try:
        # Check if token is blacklisted
        if await auth_service.is_token_blacklisted(token):
            raise InvalidTokenError

        # Decode token
        payload = security.decode_token(token)
        user_id = int(payload["sub"])

        # Get user from database
        user = await auth_service.get_user_by_id(user_id)
        if not user:
            raise AuthenticationError

        return user

    except InvalidTokenError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err


async def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """Get current active user."""
    if not current_user.is_active:
        raise InactiveUserError
    return current_user


async def get_current_admin_user(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    """Get current admin user."""
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


def check_permissions(*allowed_roles: models.UserRole):
    """Decorator for checking user roles."""

    async def permission_checker(
        current_user: models.User = Depends(get_current_active_user),
    ):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )
        return current_user

    return permission_checker
