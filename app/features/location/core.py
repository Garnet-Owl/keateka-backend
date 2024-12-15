from dataclasses import dataclass
from enum import Enum
from typing import Tuple, List


class LocationType(str, Enum):
    """Types of location updates."""

    UPDATE = "update"
    JOB_START = "job_start"
    JOB_END = "job_end"


@dataclass
class Coordinates:
    """Represents a geographic coordinate pair."""

    latitude: float
    longitude: float

    def to_tuple(self) -> Tuple[float, float]:
        return self.latitude, self.longitude

    @staticmethod
    def from_tuple(coords: Tuple[float, float]) -> "Coordinates":
        return Coordinates(latitude=coords[0], longitude=coords[1])


@dataclass
class RouteStep:
    """Represents a step in a route."""

    distance: float  # meters
    duration: float  # seconds
    instructions: str
    polyline: str


@dataclass
class RouteInfo:
    """Complete route information."""

    distance: float
    duration: float
    polyline: str
    steps: List[RouteStep]
    origin: Coordinates
    destination: Coordinates


class LocationError:
    """Error messages for location service."""

    INVALID_COORDINATES = "Invalid coordinates provided"
    JOB_NOT_FOUND = "Job not found"
    NO_LOCATION_HISTORY = "No location history found"
    UNAUTHORIZED = "Not authorized to access this resource"
    GEOCODING_FAILED = "Failed to geocode address"
    ROUTE_NOT_FOUND = "No route found"
