from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"  # Add this line


class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "KeaTeka"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    API_V1_PREFIX: str = "/api/v1"
    API_BASE_URL: str

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    RELOAD: bool = False

    # Database settings
    DATABASE_URL: str
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    SQL_ECHO: bool = False

    # Docker Database Settings
    POSTGRES_USER: str = "keateka"
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = "keateka_db"
    TEST_POSTGRES_PASSWORD: str
    TEST_DATABASE_URL: str | None = None

    # Redis settings
    REDIS_URL: str
    REDIS_POOL_SIZE: int = 10
    REDIS_POOL_TIMEOUT: int = 30

    # Security settings
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS settings
    @property
    def CORS_ORIGINS(self) -> List[str]:
        if self.ENVIRONMENT == Environment.DEVELOPMENT:
            return ["*"]
        return ["https://keateka.com", "https://api.keateka.com", "https://admin.keateka.com"]

    @property
    def CORS_METHODS(self) -> List[str]:
        return ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]

    @property
    def CORS_HEADERS(self) -> List[str]:
        return ["*"]

    CORS_CREDENTIALS: bool = True

    # Firebase settings
    FIREBASE_CREDENTIALS_PATH: str | None = None
    FIREBASE_API_KEY: str | None = None
    FIREBASE_AUTH_DOMAIN: str | None = None
    FIREBASE_PROJECT_ID: str | None = None

    # M-PESA settings
    MPESA_ENVIRONMENT: str = "sandbox"  # or "production"
    MPESA_CONSUMER_KEY: str
    MPESA_CONSUMER_SECRET: str
    MPESA_PASSKEY: str
    MPESA_BUSINESS_SHORTCODE: str  # Till/Paybill number
    MPESA_INITIATOR_NAME: str  # For B2B/B2C transactions
    MPESA_SECURITY_CREDENTIAL: str  # For B2B/B2C transactions
    MPESA_CALLBACK_BASE_URL: str = "https://api.keateka.com"

    @property
    def MPESA_CALLBACK_URLS(self) -> dict[str, str]:
        base = f"{self.MPESA_CALLBACK_BASE_URL}/api/v1/payments"
        return {
            "stk_callback": f"{base}/mpesa-callback",
            "timeout": f"{base}/mpesa-timeout",
            "result": f"{base}/mpesa-result",
        }

    # Payment settings
    PAYMENT_EXPIRY_MINUTES: int = 15
    MIN_PAYMENT_AMOUNT: float = 100.0
    MAX_PAYMENT_AMOUNT: float = 150000.0
    PAYMENT_CURRENCY: str = "KES"

    # Google Maps settings
    GOOGLE_MAPS_API_KEY: str
    GEOCODING_ENABLED: bool = True
    MAX_DISTANCE_KM: float = 25.0  # Maximum service radius

    # Rate limiting
    RATE_LIMIT_DEFAULT: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    RATE_LIMIT_BY_IP: bool = True

    # WebSocket settings
    WS_MESSAGE_QUEUE_SIZE: int = 100
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds
    WS_CONNECTION_LIFETIME: int = 3600  # 1 hour

    # File upload settings
    MAX_UPLOAD_SIZE: int = 5_242_880  # 5MB
    MAX_FILES_PER_REQUEST: int = 5

    @property
    def ALLOWED_UPLOAD_EXTENSIONS(self) -> List[str]:
        return [".jpg", ".jpeg", ".png", ".pdf", ".doc", ".docx"]

    @property
    def ALLOWED_IMAGE_TYPES(self) -> List[str]:
        return ["image/jpeg", "image/png"]

    UPLOAD_DIR: str = "uploads"
    UPLOAD_PROVIDER: str = "local"  # or "s3", "gcs"

    # AWS S3 settings (if using S3 for uploads)
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str | None = None
    AWS_BUCKET_NAME: str | None = None

    # Email settings
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_TLS: bool = True
    DEFAULT_FROM_EMAIL: str = "noreply@keateka.com"

    # SMS settings (e.g., for Africa's Talking)
    SMS_API_KEY: str | None = None
    SMS_SENDER_ID: str | None = None
    SMS_USERNAME: str | None = None

    # Notification settings
    NOTIFICATION_FROM_EMAIL: str = "noreply@keateka.com"
    SMS_ENABLED: bool = True
    EMAIL_ENABLED: bool = True
    PUSH_ENABLED: bool = True
    NOTIFICATION_BATCH_SIZE: int = 100
    NOTIFICATION_RETRY_ATTEMPTS: int = 3

    # Business settings
    BUSINESS_HOURS_START: int = 8  # 8 AM
    BUSINESS_HOURS_END: int = 20  # 8 PM
    MIN_CLEANING_DURATION: int = 60  # minutes
    BASE_RATE_PER_HOUR: float = 500.00  # KES
    SERVICE_FEE_PERCENTAGE: float = 10.0
    CANCELLATION_FEE_PERCENTAGE: float = 5.0
    MIN_ADVANCE_BOOKING_HOURS: int = 2
    MAX_ADVANCE_BOOKING_DAYS: int = 30

    # Cache settings
    CACHE_TTL_SHORT: int = 300  # 5 minutes
    CACHE_TTL_MEDIUM: int = 1800  # 30 minutes
    CACHE_TTL_LONG: int = 86400  # 24 hours

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    SENTRY_DSN: str | None = None

    class Config:
        env_file = (".env", ".env.test")
        case_sensitive = True
        use_enum_values = True

    @classmethod
    def get_test_settings(cls) -> "Settings":
        """Get settings instance for testing."""
        return cls(_env_file=".env.test", _env_file_encoding="utf-8")

    def is_development(self) -> bool:
        return self.ENVIRONMENT == Environment.DEVELOPMENT

    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    def is_testing(self) -> bool:
        return bool(self.TEST_DATABASE_URL)

    @property
    def mpesa_api_url(self) -> str:
        if self.MPESA_ENVIRONMENT == "production":
            return "https://api.safaricom.co.ke"
        return "https://sandbox.safaricom.co.ke"


settings: Settings | None = None


def init_settings():
    """Initialize settings based on environment."""
    global settings
    if settings is None:
        settings = get_settings()
    return settings


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    if os.getenv("ENVIRONMENT") == "test":
        return Settings(
            API_BASE_URL="http://testserver",
            DATABASE_URL="postgresql+asyncpg://keateka:2025_keateka_123@test-db:5432/keateka_test_db",
            POSTGRES_PASSWORD="2025_keateka_123",
            TEST_POSTGRES_PASSWORD="2025_keateka_123",
            REDIS_URL="redis://redis:6379/1",
            SECRET_KEY="test_secret_key",
            MPESA_CONSUMER_KEY="test_consumer_key",
            MPESA_CONSUMER_SECRET="test_consumer_secret",
            MPESA_PASSKEY="test_passkey",
            MPESA_BUSINESS_SHORTCODE="174379",
            MPESA_INITIATOR_NAME="testapi",
            MPESA_SECURITY_CREDENTIAL="test_credential",
            GOOGLE_MAPS_API_KEY="test_maps_key",
            ENVIRONMENT=Environment.TEST,
            DEBUG=True,
        )
    return Settings()
