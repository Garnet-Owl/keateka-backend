"""Base test class."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class BaseTest:
    """Base test class with common utilities."""

    @pytest.fixture(autouse=True)
    def setup_db(self, mock_db: AsyncSession):
        """Set up database session."""
        self.db = mock_db

    async def cleanup_db(self):
        """Clean up database after test."""
        for table in reversed(self.db.get_bind().dialect.get_table_names()):
            await self.db.execute(f"DELETE FROM {table}")
