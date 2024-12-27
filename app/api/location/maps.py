from datetime import datetime
from typing import Dict, List, Optional

import googlemaps

from app.api.location.core import (
    Coordinates,
    LocationError,
    RouteInfo,
    RouteStep,
)
from app.api.shared.config import settings
from app.api.shared.exceptions import ExternalServiceError


class GoogleMapsService:
    """Service for interacting with Google Maps APIs."""

    def __init__(self):
        """Initialize Google Maps client."""
        try:
            self.client = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
        except Exception as e:
            raise ExternalServiceError(f"Failed to initialize Google Maps client: {e!s}")

    async def geocode_address(self, address: str) -> Coordinates:
        """Convert address to coordinates."""
        try:
            result = self.client.geocode(address)
            if not result:
                raise ExternalServiceError(LocationError.GEOCODING_FAILED)

            location = result[0]["geometry"]["location"]
            return Coordinates(latitude=location["lat"], longitude=location["lng"])
        except Exception as e:
            raise ExternalServiceError(f"Geocoding failed: {e!s}")

    async def reverse_geocode(self, coords: Coordinates) -> str:
        """Convert coordinates to address."""
        try:
            result = self.client.reverse_geocode(coords.to_tuple())
            if not result:
                return ""
            return result[0]["formatted_address"]
        except Exception as e:
            raise ExternalServiceError(f"Reverse geocoding failed: {e!s}")

    async def calculate_route(
        self,
        origin: Coordinates,
        destination: Coordinates,
        departure_time: Optional[datetime] = None,
    ) -> RouteInfo:
        """Calculate route between two points."""
        try:
            result = self.client.directions(
                origin=origin.to_tuple(),
                destination=destination.to_tuple(),
                mode="driving",
                departure_time=departure_time,
                traffic_model="best_guess",
                optimize_waypoints=True,
            )

            if not result:
                raise ExternalServiceError(LocationError.ROUTE_NOT_FOUND)

            route = result[0]
            leg = route["legs"][0]

            steps = [
                RouteStep(
                    distance=step["distance"]["value"],
                    duration=step["duration"]["value"],
                    instructions=step["html_instructions"],
                    polyline=step["polyline"]["points"],
                )
                for step in leg["steps"]
            ]

            return RouteInfo(
                distance=leg["distance"]["value"],
                duration=leg["duration"]["value"],
                polyline=route["overview_polyline"]["points"],
                steps=steps,
                origin=origin,
                destination=destination,
            )
        except Exception as e:
            raise ExternalServiceError(f"Route calculation failed: {e!s}")

    async def calculate_distance_matrix(
        self,
        origins: List[Coordinates],
        destinations: List[Coordinates],
        departure_time: Optional[datetime] = None,
    ) -> List[List[Dict]]:
        """Calculate distance matrix between multiple points."""
        try:
            result = self.client.distance_matrix(
                origins=[c.to_tuple() for c in origins],
                destinations=[c.to_tuple() for c in destinations],
                mode="driving",
                departure_time=departure_time,
                traffic_model="best_guess",
            )

            if result["status"] != "OK":
                raise ExternalServiceError(f"Distance matrix calculation failed: {result['status']}")

            return [
                [
                    {
                        "distance": element["distance"]["value"],
                        "duration": element["duration"]["value"],
                        "duration_in_traffic": element.get("duration_in_traffic", {}).get("value"),
                        "status": element["status"],
                    }
                    for element in row["elements"]
                ]
                for row in result["rows"]
            ]
        except Exception as e:
            raise ExternalServiceError(f"Distance matrix calculation failed: {e!s}")

    async def snap_to_roads(self, points: List[Coordinates]) -> List[Coordinates]:
        """Snap a path to roads."""
        try:
            result = self.client.snap_to_roads(
                [{"latitude": p.latitude, "longitude": p.longitude} for p in points],
            )

            return [
                Coordinates(
                    latitude=point["location"]["latitude"],
                    longitude=point["location"]["longitude"],
                )
                for point in result.get("snappedPoints", [])
            ]
        except Exception as e:
            raise ExternalServiceError(f"Road snapping failed: {e!s}")
