# tests/shared/utils.py
import hashlib
import logging
from pathlib import Path
from typing import BinaryIO

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


def calculate_checksum(file_content: BinaryIO) -> str:
    """Calculate checksum for file content."""
    sha256 = hashlib.sha256()
    for chunk in iter(lambda: file_content.read(4096), b""):
        sha256.update(chunk)
    return sha256.hexdigest()


def verify_checksum(file_path: str, expected_checksum: str) -> bool:
    """Verify file checksum matches expected value."""
    sha256 = hashlib.sha256()
    try:
        with Path(file_path).open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
            file_checksum = sha256.hexdigest()
    except Exception:
        logger.exception("Error verifying checksum")
        return False
    else:
        return file_checksum == expected_checksum
