import os
from contextlib import contextmanager
from typing import Dict, Optional


@contextmanager
def test_env(env_vars: Optional[Dict[str, str]] = None):
    """Temporarily set environment variables for tests."""
    original = {}
    env_vars = env_vars or {}

    try:
        for key, value in env_vars.items():
            if key in os.environ:
                original[key] = os.environ[key]
            os.environ[key] = value
        yield
    finally:
        for key in env_vars:
            if key in original:
                os.environ[key] = original[key]
            else:
                del os.environ[key]
