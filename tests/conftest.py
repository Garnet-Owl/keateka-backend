import os
import pytest
import logging
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from app.shared.database import Base
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    database_url = "postgresql+asyncpg://keateka:keateka123@localhost:5432/keateka_test_db"
    engine = create_async_engine(database_url)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_database(test_engine):
    """Set up test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
async def async_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a new async database session for each test."""
    async_session_factory = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with async_session_factory() as session:
        yield session


@pytest.fixture
async def test_client():
    """Create a test client for the FastAPI application."""
    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        yield client
