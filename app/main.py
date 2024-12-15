from contextlib import asynccontextmanager
import logging
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.features.auth.routes import router as auth_router
from app.features.jobs.routes import (
    router as jobs_router,
    websocket_router as jobs_ws_router,
)
from app.features.notifications.routes import router as notifications_router
from app.shared.config import settings
from app.shared.database import DatabaseManager
from app.shared.middleware.error_handler import setup_error_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan():
    logger.info("Starting up application...")
    try:
        if not await DatabaseManager.check_connection():
            raise ConnectionError("Could not connect to database")
        logger.info("Database connection established successfully")
        yield
    except Exception:
        logger.exception("Startup failed")
        raise
    finally:
        logger.info("Shutting down application...")
        await DatabaseManager.close_connections()
        logger.info("Cleanup completed")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="KeaTeka Cleaning Service API",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

setup_error_handlers(app)


@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> Response:
    import time

    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000

    # Use string concatenation for long string
    log_msg = (
        "Method: %(method)s "
        "Path: %(path)s "
        "Status: %(status)s "
        "Time: %(time).2fms"
    )
    logger.info(
        log_msg,
        {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "time": process_time,
        },
    )
    return response


@app.get("/health")
async def health_check():
    db_healthy = await DatabaseManager.check_connection()
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(jobs_router, prefix=settings.API_V1_PREFIX)
app.include_router(jobs_ws_router, prefix=settings.API_V1_PREFIX)
app.include_router(notifications_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root() -> dict:
    """Root endpoint returning API info."""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/api/docs",
        "redoc_url": "/api/redoc",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        workers=settings.WORKERS,
    )
