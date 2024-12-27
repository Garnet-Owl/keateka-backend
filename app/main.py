import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.api.auth.routes import router as auth_router
from app.api.jobs.routes import (
    router as jobs_router,
    websocket_router as jobs_ws_router,
)
from app.api.location.routes import router as location_router
from app.api.notifications.routes import router as notifications_router
from app.api.payments.routes import router as payments_router
from app.api.shared.config import settings
from app.api.shared.database import DatabaseManager
from app.api.shared.middleware.error_handler import setup_error_handlers
from app.api.shared.middleware.request_id import RequestIDMiddleware
from app.api.shared.middleware.timing import TimingMiddleware

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL), format=settings.LOG_FORMAT)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    logger.info("Starting up application...")
    try:
        # Check database connection
        if not await DatabaseManager.check_connection():
            raise ConnectionError("Could not connect to database")
        logger.info("Database connection established successfully")

        # Additional startup tasks could go here
        logger.info("Application startup completed successfully")
        yield

    except Exception as e:
        logger.exception("Startup failed: %s", str(e))
        raise

    finally:
        logger.info("Shutting down application...")
        try:
            await DatabaseManager.close_connections()
            logger.info("Database connections closed successfully")
        except Exception as e:
            logger.error("Error during cleanup: %s", str(e))
        logger.info("Cleanup completed")


async def gzip_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    middleware = GZipMiddleware(app_=None)  # type: ignore
    return await middleware(request, call_next)


async def logging_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    start_time = time.time()
    request_id = getattr(request.state, "request_id", "unknown")

    logger.info(
        "Request started | ID: %s | Method: %s | Path: %s",
        request_id,
        request.method,
        request.url.path,
    )

    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000

        logger.info(
            "Request completed | ID: %s | Method: %s | Path: %s | Status: %s | Time: %.2fms",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            process_time,
        )

        return response

    except Exception as e:
        logger.exception(
            "Request failed | ID: %s | Method: %s | Path: %s | Error: %s",
            request_id,
            request.method,
            request.url.path,
            str(e),
        )
        raise


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    fast_app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description="KeaTeka Cleaning Service API",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Add CORS middleware
    fast_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
    )

    # Add other middlewares
    fast_app.middleware("http")(gzip_middleware)
    fast_app.middleware("http")(logging_middleware)

    # Add request ID and timing middlewares
    fast_app.add_middleware(RequestIDMiddleware)
    fast_app.add_middleware(TimingMiddleware)

    # Setup error handlers
    setup_error_handlers(fast_app)

    return fast_app


app = create_application()


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint for monitoring."""
    db_healthy = await DatabaseManager.check_connection()

    status = "healthy" if db_healthy else "unhealthy"
    status_code = 200 if db_healthy else 503

    response_data = {
        "status": status,
        "database": "connected" if db_healthy else "disconnected",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": time.time(),
    }

    return JSONResponse(content=response_data, status_code=status_code)


# API Routes
api_v1_prefix = settings.API_V1_PREFIX

# Core feature routers
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(jobs_router, prefix=api_v1_prefix)
app.include_router(jobs_ws_router, prefix=api_v1_prefix)
app.include_router(notifications_router, prefix=api_v1_prefix)
app.include_router(payments_router, prefix=api_v1_prefix)
app.include_router(location_router, prefix=api_v1_prefix)


@app.get("/")
async def root() -> dict:
    """Root endpoint returning API info."""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/api/docs",
        "redoc_url": "/api/redoc",
        "openapi_url": "/api/openapi.json",
        "health_check": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        workers=settings.WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )
