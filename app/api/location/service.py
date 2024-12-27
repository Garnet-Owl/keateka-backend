from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.location import models, schemas
from app.api.location.core import Coordinates, LocationError
from app.api.location.maps import GoogleMapsService
from app.api.location.routing import RouteCalculator
from app.api.shared.exceptions import NotFoundException


class LocationService:
    """Service for handling location-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.maps = GoogleMapsService()
        self.route_calculator = RouteCalculator(db, self.maps)

    async def update_location(
        self,
        user_id: int,
        location_data: schemas.LocationUpdate,
    ) -> models.Location:
        """Update user's location."""
        coords = Coordinates(latitude=location_data.latitude, longitude=location_data.longitude)

        # Reverse geocode to get address
        address = await self.maps.reverse_geocode(coords)

        # Create location record
        location = models.Location(
            user_id=user_id,
            latitude=coords.latitude,
            longitude=coords.longitude,
            accuracy=location_data.accuracy,
            speed=location_data.speed,
            bearing=location_data.bearing,
            address=address,
            location_type=location_data.location_type,
        )

        self.db.add(location)
        await self.db.commit()
        await self.db.refresh(location)

        return location

    async def get_latest_location(self, user_id: int) -> Optional[models.Location]:
        """Get user's most recent location."""
        result = await self.db.execute(
            select(models.Location)
            .filter(models.Location.user_id == user_id)
            .order_by(models.Location.created_at.desc())
            .limit(1)
        )
        location = result.scalar_one_or_none()
        if not location:
            raise NotFoundException(LocationError.NO_LOCATION_HISTORY)
        return location

    async def get_location_history(
        self,
        user_id: int,
        start_time: datetime,
        end_time: datetime,
    ) -> List[models.Location]:
        """Get user's location history within timeframe."""
        result = await self.db.execute(
            select(models.Location)
            .filter(
                models.Location.user_id == user_id,
                models.Location.created_at >= start_time,
                models.Location.created_at <= end_time,
            )
            .order_by(models.Location.created_at)
        )
        return result.scalars().all()

    async def calculate_route(
        self,
        user_id: int,
        job_id: int,
        route_request: schemas.RouteRequest,
    ) -> models.Route:
        """Calculate route for a job."""
        origin = Coordinates(
            latitude=route_request.origin.latitude,
            longitude=route_request.origin.longitude,
        )
        destination = Coordinates(
            latitude=route_request.destination.latitude,
            longitude=route_request.destination.longitude,
        )

        return await self.route_calculator.calculate_route(
            user_id=user_id,
            job_id=job_id,
            origin=origin,
            destination=destination,
            departure_time=route_request.departure_time,
        )

    async def optimize_routes(
        self,
        user_id: int,
        job_ids: List[int],
        start_coordinates: Optional[Coordinates] = None,
    ) -> List[Dict]:
        """Optimize routes for multiple jobs."""
        if not start_coordinates:
            last_location = await self.get_latest_location(user_id)
            start_coordinates = Coordinates(
                latitude=last_location.latitude,
                longitude=last_location.longitude,
            )

        return await self.route_calculator.optimize_route(
            user_id=user_id,
            job_ids=job_ids,
            start_location=start_coordinates,
        )

    async def get_route_history(
        self,
        job_id: int,
        user_id: int,
    ) -> List[models.Route]:
        """Get route history for a job."""
        result = await self.db.execute(
            select(models.Route)
            .filter(
                models.Route.job_id == job_id,
                models.Route.user_id == user_id,
            )
            .order_by(models.Route.created_at)
        )
        return result.scalars().all()
