from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from hamcrest import assert_that, equal_to, not_none
import pytest

from app.features.auth.exceptions import UserAlreadyExistsError
from app.features.auth.models import RefreshToken, User, UserRole
from app.features.auth.schemas import UserCreate
from app.features.auth.service import AuthService
from tests.givenpy import given, then, when


def prepare_auth_service():
    """Prepare auth service with mocked dependencies."""

    def step(context):
        context.async_session = AsyncMock()
        context.cache_manager = AsyncMock()
        context.auth_service = AuthService(
            context.async_session, context.cache_manager
        )

    return step


def prepare_user_data():
    """Prepare test user data."""

    def step(context):
        context.user_data = {
            "email": "test@example.com",
            "phone_number": "+254700000000",
            "full_name": "Test User",
            "password": "testPass123",
            "role": UserRole.CLIENT,
        }
        context.user_create = UserCreate(**context.user_data)

    return step


def prepare_mock_db():
    """Prepare database mock responses."""

    def step(context):
        async def mock_get_user_by_email():
            return None  # No existing user

        async def mock_get_user_by_id(user_id):
            return User(
                id=user_id,
                email=context.user_data["email"],
                full_name=context.user_data["full_name"],
                role=context.user_data["role"],
                is_active=True,
            )

        async def mock_get_refresh_token(token):
            return RefreshToken(
                token=token,
                user_id=1,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                is_revoked=False,
            )

        # Replace service methods with mocks
        context.auth_service.get_user_by_email = mock_get_user_by_email
        context.auth_service.get_user_by_id = mock_get_user_by_id
        context.auth_service.get_refresh_token = mock_get_refresh_token

    return step


def prepare_token_data():
    """Prepare token test data."""

    def step(context):
        context.token_data = {
            "access": {"token": "mock_access_token", "expires_in": 3600},
            "refresh": {"token": "mock_refresh_token", "expires_in": 604800},
        }

    return step


@pytest.mark.asyncio
class TestAuthService:
    async def test_create_user_with_valid_data_succeeds(self):
        """Test successful user creation with valid data."""
        with given(
            [prepare_auth_service(), prepare_user_data(), prepare_mock_db()]
        ) as context:
            with when("creating a new user with valid data"):
                user = await context.auth_service.create_user(
                    context.user_create
                )

            with then("the user should be created successfully"):
                assert_that(user, not_none())
                assert_that(user.email, equal_to(context.user_data["email"]))
                assert_that(
                    user.full_name, equal_to(context.user_data["full_name"])
                )
                assert_that(
                    context.async_session.commit.await_count, equal_to(1)
                )
                assert_that(
                    context.async_session.refresh.await_count, equal_to(1)
                )

    async def test_create_user_with_existing_email_fails(self):
        """Test user creation fails when email already exists."""
        with given(
            [
                prepare_auth_service(),
                prepare_user_data(),
            ]
        ) as context:
            # Override get_user_by_email to return existing user
            async def mock_existing_user(email):
                return User(
                    id=1,
                    email=email,
                    full_name="Existing User",
                    role=UserRole.CLIENT,
                )

            context.auth_service.get_user_by_email = mock_existing_user

            with pytest.raises(UserAlreadyExistsError) as exc_info:
                with when("attempting to create user with existing email"):
                    await context.auth_service.create_user(context.user_create)

            with then("should raise user already exists error"):
                expected_message = f"""User already exists with email:
                {context.user_data['email']}"""
                assert_that(str(exc_info.value), equal_to(expected_message))

    async def test_create_tokens_generates_valid_tokens(self):
        """Test creation of access and refresh tokens."""
        with given(
            [
                prepare_auth_service(),
                prepare_user_data(),
                prepare_token_data(),
                prepare_mock_db(),
            ]
        ) as context:
            test_user = User(
                id=1,
                email=context.user_data["email"],
                full_name=context.user_data["full_name"],
                role=context.user_data["role"],
            )

            with (
                when("generating tokens for the user"),
                patch(
                    "app.features.auth.security.create_access_token"
                ) as mock_access,
                patch(
                    "app.features.auth.security.create_refresh_token"
                ) as mock_refresh,
            ):
                mock_access.return_value = context.token_data["access"]
                mock_refresh.return_value = context.token_data["refresh"]
                tokens = await context.auth_service.create_tokens(test_user)

            with then("should return valid token data"):
                assert_that(
                    tokens["access_token"],
                    equal_to(context.token_data["access"]["token"]),
                )
                assert_that(
                    tokens["refresh_token"],
                    equal_to(context.token_data["refresh"]["token"]),
                )
                assert_that(tokens["token_type"], equal_to("bearer"))
                assert_that(
                    context.async_session.commit.await_count, equal_to(1)
                )

    async def test_refresh_tokens_with_valid_refresh_token_succeeds(self):
        """Test successful token refresh with valid refresh token."""
        with given(
            [
                prepare_auth_service(),
                prepare_user_data(),
                prepare_token_data(),
                prepare_mock_db(),
            ]
        ) as context:
            with (
                when("refreshing tokens"),
                patch(
                    "app.features.auth.security.decode_token"
                ) as mock_decode,
            ):
                mock_decode.return_value = {"sub": "1", "type": "refresh"}

                with patch.object(
                    context.auth_service, "create_tokens"
                ) as mock_create:
                    mock_create.return_value = {
                        "access_token": "new_access_token",
                        "refresh_token": "new_refresh_token",
                        "token_type": "bearer",
                        "expires_in": 3600,
                    }
                    new_tokens = await context.auth_service.refresh_tokens(
                        "valid_refresh_token"
                    )

            with then("should return new valid tokens"):
                assert_that(
                    new_tokens["access_token"], equal_to("new_access_token")
                )
                assert_that(
                    new_tokens["refresh_token"], equal_to("new_refresh_token")
                )
                assert_that(
                    context.async_session.commit.await_count, equal_to(1)
                )
