from typing import Any, Dict, Optional

from app.shared.exceptions import BaseAPIException


class AuthenticationError(BaseAPIException):
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            details=details,
        )


class InvalidCredentialsError(BaseAPIException):
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message=message, status_code=401, error_code="INVALID_CREDENTIALS")


class InvalidTokenError(BaseAPIException):
    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message=message, status_code=401, error_code="INVALID_TOKEN")


class UserNotFoundError(BaseAPIException):
    def __init__(self, identifier: str):
        super().__init__(
            message=f"User not found with identifier: {identifier}",
            status_code=404,
            error_code="USER_NOT_FOUND",
        )


class UserAlreadyExistsError(BaseAPIException):
    def __init__(self, email: str):
        super().__init__(
            message=f"User already exists with email: {email}",
            status_code=409,
            error_code="USER_EXISTS",
        )


class InactiveUserError(BaseAPIException):
    def __init__(self):
        super().__init__(
            message="User account is inactive",
            status_code=403,
            error_code="INACTIVE_USER",
        )


class UnverifiedUserError(BaseAPIException):
    def __init__(self):
        super().__init__(
            message="User account is not verified",
            status_code=403,
            error_code="UNVERIFIED_USER",
        )


class InvalidRoleError(BaseAPIException):
    def __init__(self, role: str):
        super().__init__(
            message=f"Invalid role: {role}",
            status_code=400,
            error_code="INVALID_ROLE",
        )
