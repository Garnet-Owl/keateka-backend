from typing import TYPE_CHECKING

from fastapi import APIRouter, BackgroundTasks, Depends
from typing_extensions import Annotated

from app.features.auth import models, schemas
from app.features.auth.dependencies import (
    check_permissions,
    get_auth_service,
    get_current_active_user,
)
from app.features.notifications.models import NotificationType
from app.features.notifications.service import NotificationService
from app.shared.middleware.rate_limiter import rate_limit

if TYPE_CHECKING:
    from app.features.auth.service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserResponse)
@rate_limit(limit=5, window=60)  # 5 registrations per minute
async def register_user(
    user_data: schemas.UserCreate,
    background_tasks: BackgroundTasks,
    auth_service: Annotated["AuthService", Depends(get_auth_service)],
    notification_service: Annotated[NotificationService, Depends()],
):
    """Register a new user."""
    user = await auth_service.create_user(user_data)

    # Send welcome notification in background
    background_tasks.add_task(
        notification_service.send_notification,
        user_id=user.id,
        title="Welcome to KeaTeka",
        body=f"Welcome {user.full_name}! Your account has been created successfully.",
        data=None,  # Explicitly set to None since no additional data needed
        notification_type=NotificationType.PUSH,  # Use NotificationType directly
    )

    return user


@router.post("/login", response_model=schemas.Token)
@rate_limit(limit=10, window=60)  # 10 login attempts per minute
async def login(login_data: schemas.LoginRequest, auth_service=Depends(get_auth_service)):
    """Login with email and password."""
    user = await auth_service.authenticate_user(login_data.email, login_data.password)
    return await auth_service.create_tokens(user)


@router.post("/firebase/login", response_model=schemas.Token)
@rate_limit(limit=10, window=60)
async def firebase_login(
    login_data: schemas.FirebaseLoginRequest,
    auth_service=Depends(get_auth_service),
):
    """Login with Firebase token."""
    user, _ = await auth_service.authenticate_firebase_user(login_data.firebase_token)
    return await auth_service.create_tokens(user)


@router.post("/refresh", response_model=schemas.Token)
@rate_limit(limit=20, window=60)
async def refresh_token(
    refresh_data: schemas.RefreshTokenRequest,
    auth_service=Depends(get_auth_service),
):
    """Refresh access token."""
    return await auth_service.refresh_tokens(refresh_data.refresh_token)


@router.post("/logout")
async def logout(
    token: Annotated[str, Depends(get_current_active_user)],
    auth_service=Depends(get_auth_service),
):
    """Logout and invalidate current token."""
    await auth_service.invalidate_token(token)
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=schemas.UserResponse)
async def get_current_user_info(
    current_user: Annotated[models.User, Depends(get_current_active_user)],
):
    """Get current user information."""
    return current_user


@router.put("/me", response_model=schemas.UserResponse)
async def update_current_user(
    user_data: schemas.UserUpdate,
    current_user: Annotated[models.User, Depends(get_current_active_user)],
    auth_service=Depends(get_auth_service),
):
    """Update current user information."""
    return await auth_service.update_user(current_user.id, user_data)


@router.post("/password/reset", response_model=schemas.MessageResponse)
@rate_limit(limit=5, window=300)  # 5 requests per 5 minutes
async def request_password_reset(
    reset_data: schemas.PasswordReset,
    background_tasks: BackgroundTasks,
    auth_service=Depends(get_auth_service),
    notification_service: NotificationService = Depends(),
):
    """Request password reset."""
    user = await auth_service.get_user_by_email(reset_data.email)
    if user:
        token = auth_service.create_password_reset_token(user.email)
        # Send reset email in background
        background_tasks.add_task(
            notification_service.send_notification,
            user_id=user.id,
            title="Password Reset Requested",
            body="Click the link in your email to reset your password.",
            data={"reset_token": token},
            notification_type=NotificationType.EMAIL,
        )
    return {"message": "If the email exists, password reset instructions have been sent"}


@router.post("/password/reset/confirm", response_model=schemas.MessageResponse)
@rate_limit(limit=5, window=300)
async def confirm_password_reset(
    reset_data: schemas.PasswordResetConfirm,
    auth_service=Depends(get_auth_service),
):
    """Confirm password reset."""
    await auth_service.reset_password(reset_data.token, reset_data.new_password)
    return {"message": "Password has been reset successfully"}


@router.post("/verify-email", response_model=schemas.MessageResponse)
@rate_limit(limit=5, window=300)
async def verify_email(token: str, auth_service=Depends(get_auth_service)):
    """Verify user email."""
    await auth_service.verify_email(token)
    return {"message": "Email verified successfully"}


# Admin routes
@router.get("/users", response_model=list[schemas.UserResponse])
@check_permissions(models.UserRole.ADMIN)
async def list_users(skip: int = 0, limit: int = 100, auth_service=Depends(get_auth_service)):
    """List all users (admin only)."""
    return await auth_service.list_users(skip, limit)


@router.get("/users/{user_id}", response_model=schemas.UserResponse)
@check_permissions(models.UserRole.ADMIN)
async def get_user(user_id: int, auth_service=Depends(get_auth_service)):
    """Get specific user details (admin only)."""
    return await auth_service.get_user(user_id)


@router.put("/users/{user_id}", response_model=schemas.UserResponse)
@check_permissions(models.UserRole.ADMIN)
async def update_user(
    user_id: int,
    user_data: schemas.UserUpdate,
    auth_service=Depends(get_auth_service),
):
    """Update user details (admin only)."""
    return await auth_service.update_user(user_id, user_data)


@router.delete("/users/{user_id}", response_model=schemas.MessageResponse)
@check_permissions(models.UserRole.ADMIN)
async def delete_user(user_id: int, auth_service=Depends(get_auth_service)):
    """Delete user (admin only)."""
    await auth_service.delete_user(user_id)
    return {"message": "User deleted successfully"}
