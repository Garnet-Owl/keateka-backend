from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
from typing import AsyncGenerator, Optional

from sqlalchemy import Column, DateTime, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

from app.api.shared.config import init_settings

logger = logging.getLogger(__name__)

settings = init_settings()

# Database URL constant
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Create async engine for the PostgreSQL database
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=settings.SQL_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
)

# Create sync engine for migrations and utilities
sync_engine = create_engine(
    SQLALCHEMY_DATABASE_URL.replace("+asyncpg", ""),
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create sync session factory for utilities
SyncSessionLocal = sessionmaker(
    sync_engine,
    autocommit=False,
    autoflush=False,
)

# Base class for declarative models
Base = declarative_base()


class DatabaseError(Exception):
    """Custom exception for database-related errors."""


class DatabaseManager:
    """Database management utilities."""

    _instance: Optional["DatabaseManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        self.health_check_query = text("SELECT 1")
        self._initialize_logging()

    def _initialize_logging(self) -> None:
        """Initialize database-specific logging."""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    @staticmethod
    async def check_connection() -> bool:
        """
        Check database connection health.

        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError as e:
            logger.exception(f"Database connection check failed: {e!s}")
            return False

    @staticmethod
    async def close_connections() -> None:
        """Close all database connections."""
        try:
            await engine.dispose()
            sync_engine.dispose()
        except Exception as e:
            logger.exception(f"Error closing database connections: {e!s}")
            raise DatabaseError("Failed to close database connections") from e


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


@asynccontextmanager
async def transaction(session: AsyncSession):
    """
    Transaction context manager for database operations.

    Usage:
        async with transaction(db_session) as session:
            session.add(some_model)
            await session.flush()
    """
    try:
        async with session.begin():
            yield session
    except Exception as e:
        await session.rollback()
        logger.exception(f"Transaction error: {e!s}")
        msg = f"Transaction failed: {e!s}"
        raise DatabaseError(msg) from e


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function that yields async db sessions and handles cleanup.

    Usage:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.exception(f"Database session error: {e!s}")
            await session.rollback()
            raise DatabaseError("Database session error") from e
        finally:
            await session.close()


@asynccontextmanager
async def get_sync_db() -> Session:
    """
    Context manager for synchronous database sessions.

    Usage:
        async with get_sync_db() as db:
            db.query(User).all()
    """
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()
