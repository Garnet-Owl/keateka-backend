import base64
import hashlib
import logging
import secrets
from typing import Optional, Tuple

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class SecurityUtils:
    """Utility class for security operations."""

    def __init__(self, secret_key: str) -> None:
        self.secret_key = secret_key
        self.fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret_key.encode()).digest()))

    def encrypt_data(self, data: str) -> str:
        """
        Encrypt sensitive data.

        Args:
            data: String to encrypt

        Returns:
            Encrypted string in base64 format
        """
        try:
            return self.fernet.encrypt(data.encode()).decode()
        except Exception as e:
            logger.exception(f"Encryption error: {e!s}")
            raise

    def decrypt_data(self, encrypted_data: str) -> str:
        """
        Decrypt encrypted data.

        Args:
            encrypted_data: Encrypted string in base64 format

        Returns:
            Decrypted string
        """
        try:
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.exception(f"Decryption error: {e!s}")
            raise

    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        Generate cryptographically secure random token.

        Args:
            length: Desired length of the token

        Returns:
            Secure random token string
        """
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_api_key() -> Tuple[str, str]:
        """
        Generate API key and secret.
        Returns tuple of (api_key, api_secret)
        """
        api_key = secrets.token_urlsafe(16)
        api_secret = secrets.token_urlsafe(32)
        return api_key, api_secret

    def hash_sensitive_data(self, data: str) -> str:
        """
        Create one-way hash of sensitive data.

        Args:
            data: Data to hash

        Returns:
            Hash string
        """
        return hashlib.sha256(f"{data}{self.secret_key}".encode()).hexdigest()

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal attacks.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        return "".join(c for c in filename if c.isalnum() or c in "._-")

    @staticmethod
    def validate_file_size(file_size: int, max_size: int) -> bool:
        """
        Validate file size against maximum allowed size.

        Args:
            file_size: Size of file in bytes
            max_size: Maximum allowed size in bytes

        Returns:
            True if file size is valid
        """
        return file_size <= max_size

    @staticmethod
    def validate_file_type(content_type: str, allowed_types: list) -> bool:
        """
        Validate file content type.

        Args:
            content_type: MIME type of the file
            allowed_types: List of allowed MIME types

        Returns:
            True if content type is allowed
        """
        return content_type in allowed_types


# Content Security Policy (CSP) configuration
class CSPConfig:
    """Content Security Policy configuration."""

    @staticmethod
    def get_default_policy() -> str:
        """Get default CSP policy string."""
        directives = {
            "default-src": ["'self'"],
            "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
            "style-src": ["'self'", "'unsafe-inline'"],
            "img-src": ["'self'", "data:", "https:"],
            "font-src": ["'self'", "data:", "https:"],
            "connect-src": ["'self'"],
            "frame-ancestors": ["'none'"],
            "form-action": ["'self'"],
        }

        return "; ".join(f"{key} {' '.join(values)}" for key, values in directives.items())

    @staticmethod
    def get_strict_policy() -> str:
        """Get strict CSP policy string."""
        directives = {
            "default-src": ["'none'"],
            "script-src": ["'self'"],
            "style-src": ["'self'"],
            "img-src": ["'self'"],
            "font-src": ["'self'"],
            "connect-src": ["'self'"],
            "frame-ancestors": ["'none'"],
            "form-action": ["'self'"],
            "base-uri": ["'self'"],
            "object-src": ["'none'"],
        }

        return "; ".join(f"{key} {' '.join(values)}" for key, values in directives.items())


# Security Headers Configuration
class SecurityHeaders:
    """Security headers configuration."""

    @staticmethod
    def get_default_headers() -> dict:
        """Get default security headers."""
        return {
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        }

    @staticmethod
    def get_strict_headers() -> dict:
        """Get strict security headers."""
        headers = SecurityHeaders.get_default_headers()
        headers.update(
            {
                "Cross-Origin-Embedder-Policy": "require-corp",
                "Cross-Origin-Opener-Policy": "same-origin",
                "Cross-Origin-Resource-Policy": "same-origin",
            }
        )
        return headers


# CORS Configuration
class CORSConfig:
    """CORS configuration utility."""

    @staticmethod
    def get_default_config() -> dict:
        """Get default CORS configuration."""
        return {
            "allow_origins": ["*"],
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["*"],
            "allow_credentials": True,
            "max_age": 3600,
        }

    @staticmethod
    def get_strict_config() -> dict:
        """Get strict CORS configuration."""
        return {
            "allow_origins": [],  # Must be explicitly set
            "allow_methods": ["GET", "POST"],
            "allow_headers": ["Authorization", "Content-Type"],
            "allow_credentials": False,
            "max_age": 3600,
        }


# File Upload Security
class FileUploadSecurity:
    """File upload security utilities."""

    ALLOWED_IMAGE_TYPES = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
    ]

    ALLOWED_DOCUMENT_TYPES = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    ]

    @staticmethod
    def validate_upload(
        file_size: int,
        content_type: str,
        filename: str,
        max_size: int,
        allowed_types: Optional[list] = None,
    ) -> bool:
        """
        Validate file upload.

        Args:
            file_size: Size of file in bytes
            content_type: MIME type of the file
            filename: Original filename
            max_size: Maximum allowed size in bytes
            allowed_types: List of allowed MIME types

        Returns:
            True if file is valid
        """
        if not SecurityUtils.validate_file_size(file_size, max_size):
            return False

        if allowed_types and not SecurityUtils.validate_file_type(content_type, allowed_types):
            return False

        sanitized_filename = SecurityUtils.sanitize_filename(filename)
        return sanitized_filename
