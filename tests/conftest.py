import os
import pytest


def pytest_configure():
    """Configure test environment before test collection."""
    os.environ["ENVIRONMENT"] = "test"

    # Force reload of settings for tests
    from app.shared.config import init_settings

    init_settings()


@pytest.fixture(autouse=True)
def test_environment():
    """Ensure test environment for all tests."""
    previous_env = os.getenv("ENVIRONMENT")
    os.environ["ENVIRONMENT"] = "test"
    yield
    if previous_env is not None:
        os.environ["ENVIRONMENT"] = previous_env
