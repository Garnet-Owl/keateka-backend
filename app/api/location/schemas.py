from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.api.location.core import LocationType


class CoordinatesBase(BaseModel):
    """Base schema for coordinates."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class LocationUpdate(CoordinatesBase):
    """Schema for location updates."""

    accuracy: Optional[float] = Field(None, ge=0)
    speed: Optional[float] = Field(None, ge=0)
    bearing: Optional[float] = Field(None, ge=0, le=360)
    location_type: LocationType = Field(default=LocationType.UPDATE)


class LocationResponse(CoordinatesBase):
    """Schema for location responses."""

    id: int
    user_id: int
    accuracy: Optional[float]
    speed: Optional[float]
    bearing: Optional[float]
    address: Optional[str]
    location_type: LocationType
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RouteRequest(BaseModel):
    """Schema for route calculation requests."""

    origin: CoordinatesBase
    destination: CoordinatesBase
    departure_time: Optional[datetime] = None


class RouteStepResponse(BaseModel):
    """Schema for route step responses."""

    distance: float
    duration: float
    instructions: str
    polyline: str


class RouteResponse(BaseModel):
    """Schema for route calculation responses."""

    distance: float
    duration: float
    eta: datetime
    polyline: str
    steps: List[RouteStepResponse]
    origin: CoordinatesBase
    destination: CoordinatesBase

    class Config:
        from_attributes = True


class ETAUpdate(BaseModel):
    """Schema for ETA updates."""

    job_id: int
    new_eta: datetime
    delay_minutes: Optional[int] = None
