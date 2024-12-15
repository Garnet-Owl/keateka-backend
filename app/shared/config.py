from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "KeaTeka"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

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

    # CORS settings
    @property
    def CORS_ORIGINS(self) -> list[str]:
        return ["*"]

    @property
    def CORS_METHODS(self) -> list[str]:
        return ["*"]

    @property
    def CORS_HEADERS(self) -> list[str]:
        return ["*"]

    CORS_CREDENTIALS: bool = True

    # Firebase settings
    FIREBASE_CREDENTIALS_PATH: str | None = None

    # M-PESA settings
    MPESA_CONSUMER_KEY: str
    MPESA_CONSUMER_SECRET: str
    MPESA_PASSKEY: str
    MPESA_BUSINESS_SHORT_CODE: str
    MPESA_CALLBACK_URL: str

    # Google Maps settings
    GOOGLE_MAPS_API_KEY: str

    # Rate limiting
    RATE_LIMIT_DEFAULT: int = 100
    RATE_LIMIT_WINDOW: int = 60

    # WebSocket settings
    WS_MESSAGE_QUEUE_SIZE: int = 100
    WS_HEARTBEAT_INTERVAL: int = 30

    # File upload settings
    MAX_UPLOAD_SIZE: int = 5_242_880  # 5MB

    @property
    def ALLOWED_UPLOAD_EXTENSIONS(self) -> list[str]:
        return [".jpg", ".jpeg", ".png", ".pdf"]

    UPLOAD_DIR: str = "uploads"

    # Notification settings
    NOTIFICATION_FROM_EMAIL: str = "noreply@keateka.com"
    SMS_ENABLED: bool = True
    EMAIL_ENABLED: bool = True
    PUSH_ENABLED: bool = True

    # Business settings
    BUSINESS_HOURS_START: int = 8  # 8 AM
    BUSINESS_HOURS_END: int = 20  # 8 PM
    MIN_CLEANING_DURATION: int = 60  # minutes
    BASE_RATE_PER_HOUR: float = 500.00  # KES
    SERVICE_FEE_PERCENTAGE: float = 10.0

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Usage:
        settings = get_settings()
        database_url = settings.DATABASE_URL
    """
    return Settings()


# Create global settings instance
settings = get_settings()
