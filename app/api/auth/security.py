from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Union

from firebase_admin import auth as firebase_auth
import jwt
from passlib.context import CryptContext

from app.api.auth.exceptions import InvalidTokenError
from app.api.shared.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Create password hash."""
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, int],
    role: str,
    token_type: str = "access",
    firebase_uid: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> Dict[str, str]:
    """Create JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(subject),
        "role": role,
        "type": token_type,
        "exp": expire,
    }
    if firebase_uid:
        to_encode["firebase_uid"] = firebase_uid

    encoded_token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    return {
        "token": encoded_token,
        "expires_in": int((expire - datetime.now(timezone.utc)).total_seconds()),
    }


def create_refresh_token(
    subject: Union[str, int],
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> Dict[str, str]:
    """Create JWT refresh token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": str(subject),
        "role": role,
        "type": "refresh",
        "exp": expire,
    }

    encoded_token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    return {
        "token": encoded_token,
        "expires_in": int((expire - datetime.now(timezone.utc)).total_seconds()),
    }


def decode_token(token: str) -> Dict:
    """Decode and verify JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        if payload.get("type") not in ["access", "refresh"]:
            raise InvalidTokenError("Invalid token type")

        return payload
    except jwt.ExpiredSignatureError:
        raise InvalidTokenError("Token has expired")
    except jwt.InvalidTokenError:
        raise InvalidTokenError("Invalid token")


async def verify_firebase_token(token: str) -> dict:
    """Verify Firebase ID token."""
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        msg = f"Invalid Firebase token: {e!s}"
        raise InvalidTokenError(msg)


def get_token_data(token: str) -> Dict:
    """Extract data from token."""
    try:
        payload = decode_token(token)
        return {
            "sub": payload["sub"],
            "exp": datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            "type": payload["type"],
            "role": payload["role"],
        }
    except Exception as e:
        msg = f"Failed to decode token: {e!s}"
        raise InvalidTokenError(msg)


def create_email_verification_token(email: str) -> str:
    """Create token for email verification."""
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode = {"sub": email, "type": "email_verify", "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_password_reset_token(email: str) -> str:
    """Create token for password reset."""
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    to_encode = {"sub": email, "type": "password_reset", "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
