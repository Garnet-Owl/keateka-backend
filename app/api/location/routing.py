from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.jobs.models import Job, JobStatus
from app.api.location.core import Coordinates, LocationError
from app.api.location.maps import GoogleMapsService
from app.api.location.models import Route
from app.api.shared.exceptions import BusinessLogicError, NotFoundException


class RouteCalculator:
    """Service for route calculations and optimizations."""

    def __init__(self, db: AsyncSession, maps_service: GoogleMapsService):
        self.db = db
        self.maps = maps_service

    async def calculate_route(
        self,
        user_id: int,
        job_id: int,
        origin: Coordinates,
        destination: Coordinates,
        departure_time: Optional[datetime] = None,
    ) -> Route:
        """Calculate and store route for a job."""
        # Verify job exists and belongs to user
        job = await self._get_job(job_id, user_id)
        if not job:
            raise NotFoundException(LocationError.JOB_NOT_FOUND)

        # Calculate route using Google Maps
        route_info = await self.maps.calculate_route(
            origin=origin,
            destination=destination,
            departure_time=departure_time,
        )

        # Create route record
        route = Route(
            user_id=user_id,
            job_id=job_id,
            origin_lat=origin.latitude,
            origin_lng=origin.longitude,
            destination_lat=destination.latitude,
            destination_lng=destination.longitude,
            distance=route_info.distance,
            duration=route_info.duration,
            encoded_polyline=route_info.polyline,
            eta=datetime.now(timezone.utc) + timedelta(seconds=route_info.duration),
        )

        self.db.add(route)
        await self.db.commit()
        await self.db.refresh(route)

        return route

    async def optimize_route(
        self,
        user_id: int,
        job_ids: List[int],
        start_location: Coordinates,
    ) -> List[Dict]:
        """Optimize route for multiple jobs."""
        # Get all jobs
        jobs = await self._get_jobs(job_ids, user_id)
        if not jobs:
            raise BusinessLogicError("No valid jobs found")

        # Create origins and destinations
        destinations = [Coordinates(latitude=job.latitude, longitude=job.longitude) for job in jobs]

        # Calculate distance matrix
        matrix = await self.maps.calculate_distance_matrix(
            origins=[start_location],
            destinations=destinations,
        )

        # Optimize using nearest neighbor algorithm
        current_point = 0  # Start location
        unvisited = list(range(len(destinations)))
        route = []

        while unvisited:
            nearest = min(
                unvisited,
                key=lambda x, cp=current_point: matrix[cp][x]["duration"],
            )

            route.append(
                {
                    "job_id": jobs[nearest].id,
                    "duration": matrix[current_point][nearest]["duration"],
                    "distance": matrix[current_point][nearest]["distance"],
                }
            )

            current_point = nearest + 1
            unvisited.remove(nearest)

        return route

    async def _get_job(self, job_id: int, user_id: int) -> Optional[Job]:
        """Get job and verify access."""
        result = await self.db.execute(
            select(Job).filter(
                Job.id == job_id,
                Job.status != JobStatus.CANCELLED,
            ),
        )
        job = result.scalar_one_or_none()

        if not job:
            return None

        if job.client_id != user_id and job.cleaner_id != user_id:
            raise BusinessLogicError(LocationError.UNAUTHORIZED)

        return job

    async def _get_jobs(self, job_ids: List[int], user_id: int) -> List[Job]:
        """Get multiple jobs and verify access."""
        result = await self.db.execute(
            select(Job).filter(
                Job.id.in_(job_ids),
                Job.status != JobStatus.CANCELLED,
            ),
        )
        jobs = result.scalars().all()

        return [job for job in jobs if job.client_id == user_id or job.cleaner_id == user_id]
