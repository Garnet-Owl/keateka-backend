from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.features.auth.dependencies import get_current_active_user
from app.features.auth.models import User, UserRole
from app.features.location import schemas
from app.features.location.core import Coordinates, LocationError
from app.features.location.service import LocationService
from app.shared.database import AsyncSession, get_db
from app.shared.exceptions import BusinessLogicError
from app.shared.middleware.rate_limiter import rate_limit

router = APIRouter(prefix="/api/v1/location", tags=["location"])


async def get_location_service(
    db: AsyncSession = Depends(get_db),
) -> LocationService:
    """Dependency for location service."""
    return LocationService(db)


@router.post("/update", response_model=schemas.LocationResponse)
@rate_limit(limit=60, window=60)  # 1 update per second max
async def update_location(
    location: schemas.LocationUpdate,
    current_user: User = Depends(get_current_active_user),
    service: LocationService = Depends(get_location_service),
):
    """
    Update user's current location.

    Rate limited to prevent excessive updates.
    """
    return await service.update_location(current_user.id, location)


@router.get("/current", response_model=schemas.LocationResponse)
async def get_current_location(
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    service: LocationService = Depends(get_location_service),
):
    """
    Get user's current location.

    Admins can query other users' locations.
    """
    # Only allow admins to query other users' locations
    if user_id and user_id != current_user.id:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=LocationError.UNAUTHORIZED,
            )

    target_user_id = user_id or current_user.id
    return await service.get_latest_location(target_user_id)


@router.get("/history", response_model=List[schemas.LocationResponse])
async def get_location_history(
    start_time: datetime,
    end_time: datetime,
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    service: LocationService = Depends(get_location_service),
):
    """
    Get user's location history within a timeframe.

    Admins can query other users' history.
    """
    if user_id and user_id != current_user.id:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=LocationError.UNAUTHORIZED,
            )

    target_user_id = user_id or current_user.id
    return await service.get_location_history(target_user_id, start_time, end_time)


@router.post("/routes/{job_id}", response_model=schemas.RouteResponse)
@rate_limit(limit=30, window=60)  # 30 requests per minute
async def calculate_route(
    job_id: int,
    route_request: schemas.RouteRequest,
    current_user: User = Depends(get_current_active_user),
    service: LocationService = Depends(get_location_service),
):
    """
    Calculate route for a job.

    Rate limited to prevent excessive API calls.
    """
    try:
        return await service.calculate_route(
            current_user.id,
            job_id,
            route_request,
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/routes/{job_id}", response_model=List[schemas.RouteResponse])
async def get_route_history(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    service: LocationService = Depends(get_location_service),
):
    """Get route history for a specific job."""
    return await service.get_route_history(job_id, current_user.id)


@router.post("/routes/optimize", response_model=List[dict])
@rate_limit(limit=20, window=60)  # 20 requests per minute
async def optimize_routes(
    job_ids: List[int],
    start_location: Optional[schemas.CoordinatesBase] = None,
    current_user: User = Depends(get_current_active_user),
    service: LocationService = Depends(get_location_service),
):
    """
    Optimize routes for multiple jobs.

    If start_location is not provided, uses user's last known location.
    """
    start_coords = None
    if start_location:
        start_coords = Coordinates(
            latitude=start_location.latitude,
            longitude=start_location.longitude,
        )

    try:
        return await service.optimize_routes(
            user_id=current_user.id,
            job_ids=job_ids,
            start_coordinates=start_coords,
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
