from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.shared.database import Base, TimestampMixin


class Location(Base, TimestampMixin):
    """Tracks cleaner locations."""

    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)  # GPS accuracy in meters
    speed = Column(Float, nullable=True)  # Speed in m/s
    bearing = Column(Float, nullable=True)  # Direction in degrees
    address = Column(String, nullable=True)  # Reverse geocoded address
    location_type = Column(String, nullable=False)  # from LocationType enum

    # Composite index for spatial queries
    __table_args__ = (Index("idx_locations_coordinates", "latitude", "longitude"),)

    # Relationships
    user = relationship("User", back_populates="locations")


class Route(Base, TimestampMixin):
    """Stores calculated routes between points."""

    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"))
    origin_lat = Column(Float, nullable=False)
    origin_lng = Column(Float, nullable=False)
    destination_lat = Column(Float, nullable=False)
    destination_lng = Column(Float, nullable=False)
    distance = Column(Float, nullable=False)  # Distance in meters
    duration = Column(Float, nullable=False)  # Duration in seconds
    encoded_polyline = Column(String, nullable=False)  # Google's encoded polyline
    eta = Column(DateTime(timezone=True), nullable=False)  # Estimated arrival time

    # Relationships
    user = relationship("User", back_populates="routes")
    job = relationship("Job", back_populates="routes")
