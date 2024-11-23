from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime  # Add this import
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
    RateLimiter, times=5, seconds=60
)  # 5 requests  # per minute


@app.get("/")
async def root() -> Dict[str, str]:
    return {
        "message": "Welcome to KeaTeka API",
        "status": "active",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
