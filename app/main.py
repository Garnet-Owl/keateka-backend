from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
from typing import Dict

from app.middleware.rate_limiter import RateLimiter

# Create FastAPI instance
app = FastAPI(
    title="KeaTeka API",
    description="Backend API for KeaTeka Cleaning Service",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting to auth endpoints
app.add_middleware(
    RateLimiter,
    times=5,  # 5 requests
    seconds=60,  # per minute
)


@app.get("/")
async def root() -> Dict[str, str]:
    return {
        "message": "Welcome to KeaTeka API",
        "status": "active",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    current_time = datetime.now(timezone.utc)  # Compliant
    return {"status": "healthy", "timestamp": current_time.isoformat()}


# Example of handling Unix timestamps if needed
def from_timestamp(timestamp: float) -> datetime:
    """Convert Unix timestamp to timezone-aware datetime."""
    return datetime.fromtimestamp(timestamp, timezone.utc)  # Compliant


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
