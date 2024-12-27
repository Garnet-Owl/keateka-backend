from datetime import datetime, timezone
from unittest.mock import MagicMock

from hamcrest import (
    assert_that,
    equal_to,
    has_length,
    instance_of,
)

from app.api.location.core import Coordinates, LocationType
from app.api.location.models import Location, Route
from app.api.location.schemas import LocationUpdate
from app.api.location.service import LocationService
from app.tests.givenpy import given, then, when


def prepare_service():
    """Prepare LocationService with mocked dependencies."""

    def step(context):
        context.db_session = MagicMock()
        context.service = LocationService(context.db_session)
        # Mock Google Maps service
        context.service.maps = MagicMock()
        context.service.maps.reverse_geocode.return_value = "123 Test Street"

    return step


def prepare_location_data():
    """Prepare test location data."""

    def step(context):
        context.location_data = LocationUpdate(
            latitude=1.2345,
            longitude=2.3456,
            accuracy=10.0,
            speed=5.0,
            bearing=90.0,
            location_type=LocationType.UPDATE,
        )
        context.user_id = 1

    return step


def prepare_route_data():
    """Prepare test route data."""

    def step(context):
        context.route_coords = {
            "origin": Coordinates(latitude=1.2345, longitude=2.3456),
            "destination": Coordinates(latitude=3.4567, longitude=4.5678),
        }
        context.job_id = 1
        context.user_id = 1

        # Mock route calculation response
        context.route_response = {
            "distance": 1000.0,  # meters
            "duration": 600.0,  # seconds
            "polyline": "test_polyline",
            "steps": [],
        }
        context.service.route_calculator.maps.calculate_route.return_value = context.route_response

    return step


def prepare_route_optimization_data():
    """Prepare test data for route optimization."""

    def step(context):
        context.job_ids = [1, 2, 3]
        context.start_coords = Coordinates(latitude=1.2345, longitude=2.3456)

        # Mock distance matrix response
        context.distance_matrix = [
            [
                {"duration": 600, "distance": 1000},
                {"duration": 900, "distance": 1500},
                {"duration": 1200, "distance": 2000},
            ],
        ]
        context.service.route_calculator.maps.calculate_distance_matrix.return_value = context.distance_matrix

        # Mock jobs query response
        test_jobs = [
            MagicMock(id=1, latitude=2.3456, longitude=3.4567),
            MagicMock(id=2, latitude=3.4567, longitude=4.5678),
            MagicMock(id=3, latitude=4.5678, longitude=5.6789),
        ]
        context.service.route_calculator._get_jobs = MagicMock(return_value=test_jobs)

    return step


class TestLocationService:
    """Test location service functionality."""

    async def test_update_location_creates_location_record(self):
        """Test that updating location creates a new location record."""
        with given([prepare_service(), prepare_location_data()]) as context:
            service = context.service
            location_data = context.location_data
            user_id = context.user_id

            with when("updating location"):
                service.db.commit = MagicMock()  # Mock commit
                location = await service.update_location(user_id, location_data)

            with then("a location record should be created"):
                assert_that(location, instance_of(Location))
                assert_that(location.latitude, equal_to(location_data.latitude))
                assert_that(location.longitude, equal_to(location_data.longitude))
                assert_that(location.address, equal_to("123 Test Street"))
                assert_that(service.db.commit.called, equal_to(True))

    async def test_calculate_route_returns_route_info(self):
        """Test that route calculation returns proper route information."""
        with given([prepare_service(), prepare_route_data()]) as context:
            service = context.service
            coords = context.route_coords
            job_id = context.job_id
            user_id = context.user_id

            with when("calculating route"):
                route = await service.calculate_route(
                    user_id=user_id,
                    job_id=job_id,
                    origin=coords["origin"],
                    destination=coords["destination"],
                )

            with then("route information should be returned"):
                assert_that(route, instance_of(Route))
                assert_that(route.distance, equal_to(1000.0))
                assert_that(route.duration, equal_to(600.0))
                assert_that(route.encoded_polyline, equal_to("test_polyline"))

    async def test_optimize_routes_returns_ordered_route(self):
        """Test that route optimization returns routes in optimal order."""
        with given([prepare_service(), prepare_route_optimization_data()]) as context:
            service = context.service
            job_ids = context.job_ids
            start_coords = context.start_coords

            with when("optimizing routes"):
                optimized_routes = await service.optimize_routes(
                    user_id=context.user_id,
                    job_ids=job_ids,
                    start_coordinates=start_coords,
                )

            with then("routes should be ordered by duration"):
                assert_that(optimized_routes, has_length(3))
                # Check routes are ordered correctly based on duration
                durations = [route["duration"] for route in optimized_routes]
                assert_that(durations, equal_to(sorted(durations)))

    async def test_get_latest_location_returns_most_recent(self):
        """Test that getting latest location returns most recent record."""
        with given([prepare_service(), prepare_location_data()]) as context:
            service = context.service
            user_id = context.user_id

            # Mock database response
            latest_location = Location(
                id=1,
                user_id=user_id,
                latitude=1.2345,
                longitude=2.3456,
                created_at=datetime.now(timezone.utc),
            )
            service.db.execute.return_value.scalar_one_or_none.return_value = latest_location

            with when("getting latest location"):
                location = await service.get_latest_location(user_id)

            with then("most recent location should be returned"):
                assert_that(location, equal_to(latest_location))
                assert_that(location.user_id, equal_to(user_id))
