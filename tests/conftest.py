import os
from typing import AsyncGenerator, Generator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

# Use test database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+asyncpg://keateka:{os.getenv('DB_PASSWORD')}@test-db:5432/keateka_test_db",
)


@pytest.fixture(scope="session")
def engine() -> Generator[AsyncEngine, None, None]:
    """Create and yield test database engine."""
    engine = create_async_engine(DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
async def db_session(
    engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Create and yield test database session."""
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session() as session:
        yield session
