"""Test configuration and fixtures."""

import os
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Set test environment before any imports
os.environ["ENVIRONMENT"] = "test"

# Now import settings after environment is set
from app.api.shared.config import init_settings
from app.api.shared.database import Base

# Initialize settings
settings = init_settings()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    # Use localhost if POSTGRES_HOST not set (local development)
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_url = f"postgresql+asyncpg://keateka:2025_keateka_123@{db_host}:{db_port}/keateka_test_db"

    engine = create_async_engine(
        db_url,
        echo=True,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def test_db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Get test database session."""
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(autouse=True)
def test_environment():
    """Ensure test environment for all tests."""
    previous_env = os.getenv("ENVIRONMENT")
    os.environ["ENVIRONMENT"] = "test"
    yield
    if previous_env:
        os.environ["ENVIRONMENT"] = previous_env
