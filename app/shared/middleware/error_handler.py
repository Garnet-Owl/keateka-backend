from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.shared.exceptions import BaseAPIException

logger = logging.getLogger(__name__)


async def error_handler(request: Request, exc: HTTPException | BaseAPIException | Exception) -> JSONResponse:
    """
    Global error handler middleware for FastAPI application.
    Handles different types of exceptions and returns appropriate JSON responses.
    """

    error_response: dict[str, Any] = {
        "error": "Internal Server Error",
        "message": str(exc),
        "path": request.url.path,
        "method": request.method,
    }

    if isinstance(exc, BaseAPIException):
        # Handle our custom API exceptions
        error_response = exc.to_dict()
        status_code = exc.status_code
    elif isinstance(exc, HTTPException):
        # Handle FastAPI HTTP exceptions
        error_response.update(
            {
                "error": "HTTP Error",
                "message": exc.detail,
                "status_code": exc.status_code,
            }
        )
        status_code = exc.status_code
    else:
        # Handle unexpected exceptions
        logger.exception(
            "Unexpected error occurred",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error": str(exc),
            },
        )
        status_code = 500
        if not error_response.get("message"):
            error_response["message"] = "An unexpected error occurred"

    return JSONResponse(status_code=status_code, content=error_response)


def setup_error_handlers(app):
    """Configure error handlers for the FastAPI application."""
    app.add_exception_handler(HTTPException, error_handler)
    app.add_exception_handler(BaseAPIException, error_handler)
    app.add_exception_handler(Exception, error_handler)
