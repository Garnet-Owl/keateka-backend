import logging
from datetime import datetime, timedelta, UTC
from typing import Any, Union, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityError(Exception):
    pass


class TokenError(SecurityError):
    pass


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    try:
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        to_encode = {"exp": expire, "sub": str(subject)}
        return jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
    except Exception as e:
        logger.error(f"Failed to create access token: {str(e)}")
        raise SecurityError("Token creation failed") from e


def create_refresh_token(subject: Union[str, Any]) -> str:
    try:
        expire = datetime.now(UTC) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
        return jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
    except Exception as e:
        logger.error(f"Failed to create refresh token: {str(e)}")
        raise SecurityError("Refresh token creation failed") from e


def decode_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        if payload.get("type") != "refresh":
            logger.warning("Invalid token type detected")
            raise TokenError("Invalid token type")

        return payload
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise TokenError("Invalid or expired token") from e
    except Exception as e:
        logger.error(f"Unexpected error decoding token: {str(e)}")
        raise SecurityError("Token processing failed") from e


def decode_verification_token(token: str) -> dict:
    try:
        return jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError as e:
        logger.error(f"Verification token decode error: {str(e)}")
        raise TokenError("Invalid or expired verification token") from e
    except Exception as e:
        logger.error(f"Unexpected error decoding verification token: {str(e)}")
        raise SecurityError("Verification token processing failed") from e


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification failed: {str(e)}")
        raise SecurityError("Password verification failed") from e


def get_password_hash(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Password hashing failed: {str(e)}")
        raise SecurityError("Password hashing failed") from e
