from app.shared.exceptions import (
    AuthenticationError,
    BaseAPIException,
    BusinessLogicError,
    ExternalServiceError,
    NotFoundException,
    ValidationError,
)
from tests.givenpy import given, then, when


def prepare_base_exception_all_fields():
    def step(context):
        context.message = "Test error"
        context.status_code = 400
        context.error_code = "TEST_ERROR"
        context.details = {"field": "value"}

    return step


def prepare_base_exception_required_fields():
    def step(context):
        context.message = "Test error"

    return step


def prepare_auth_error_with_details():
    def step(context):
        context.message = "Invalid credentials"
        context.details = {"attempt": 3}

    return step


def prepare_validation_error():
    def step(context):
        context.message = "Invalid input data"
        context.details = {
            "field": "email",
            "error": "invalid format",
            "value": "invalid@email",
        }

    return step


def prepare_multiple_validation_errors():
    def step(context):
        context.details = {
            "errors": [
                {"field": "email", "error": "invalid format"},
                {"field": "phone", "error": "required"},
            ]
        }

    return step


def prepare_not_found_details():
    def step(context):
        context.message = "User not found"
        context.details = {"resource_type": "user", "resource_id": 123}

    return step


def prepare_service_error_details():
    def step(context):
        context.message = "Payment service unavailable"
        context.details = {
            "service": "payment_gateway",
            "error_code": "CONNECTION_TIMEOUT",
            "retry_after": 30,
        }

    return step


def prepare_business_error_details():
    def step(context):
        context.message = "Cannot cancel job in progress"
        context.details = {
            "rule": "job_cancellation",
            "current_status": "in_progress",
            "allowed_statuses": ["pending", "scheduled"],
        }

    return step


class TestBaseAPIException:
    def test_creates_error_dict_with_all_fields(self):
        with given([prepare_base_exception_all_fields()]) as context:
            exception = BaseAPIException(
                message=context.message,
                status_code=context.status_code,
                error_code=context.error_code,
                details=context.details,
            )

        with when("converting to dictionary"):
            error_dict = exception.to_dict()

        with then("should contain all error information"):
            assert error_dict["error"] == "TEST_ERROR"
            assert error_dict["message"] == "Test error"
            assert error_dict["status_code"] == 400
            assert error_dict["details"] == {"field": "value"}

    def test_creates_error_dict_without_optional_fields(self):
        with given([prepare_base_exception_required_fields()]) as context:
            exception = BaseAPIException(message=context.message)

        with when("converting to dictionary"):
            error_dict = exception.to_dict()

        with then("should contain default values"):
            assert error_dict["error"] == "BaseAPIException"
            assert error_dict["message"] == "Test error"
            assert error_dict["status_code"] == 500
            assert "details" not in error_dict


class TestAuthenticationError:
    def test_creates_with_custom_message_and_details(self):
        with given([prepare_auth_error_with_details()]) as context:
            exception = AuthenticationError(message=context.message, details=context.details)

        with when("creating authentication error"):
            error_dict = exception.to_dict()

        with then("should contain authentication-specific info"):
            assert error_dict["error"] == "AUTHENTICATION_ERROR"
            assert error_dict["message"] == context.message
            assert error_dict["status_code"] == 401
            assert error_dict["details"] == context.details

    def test_creates_with_default_message(self):
        with given([]):
            exception = AuthenticationError()

        with when("converting to dictionary"):
            error_dict = exception.to_dict()

        with then("should contain default values"):
            assert error_dict["error"] == "AUTHENTICATION_ERROR"
            assert error_dict["message"] == "Authentication failed"
            assert error_dict["status_code"] == 401


class TestValidationError:
    def test_creates_with_field_validation_details(self):
        with given([prepare_validation_error()]) as context:
            exception = ValidationError(message=context.message, details=context.details)

        with when("creating validation error"):
            error_dict = exception.to_dict()

        with then("should contain validation-specific info"):
            assert error_dict["error"] == "VALIDATION_ERROR"
            assert error_dict["message"] == context.message
            assert error_dict["status_code"] == 400
            assert error_dict["details"] == context.details

    def test_creates_with_multiple_field_errors(self):
        with given([prepare_multiple_validation_errors()]) as context:
            exception = ValidationError(details=context.details)

        with when("creating validation error"):
            error_dict = exception.to_dict()

        with then("should contain all validation errors"):
            assert error_dict["error"] == "VALIDATION_ERROR"
            assert error_dict["status_code"] == 400
            assert len(error_dict["details"]["errors"]) == 2


class TestNotFoundException:
    def test_creates_with_resource_details(self):
        with given([prepare_not_found_details()]) as context:
            exception = NotFoundException(message=context.message, details=context.details)

        with when("creating not found error"):
            error_dict = exception.to_dict()

        with then("should contain resource details"):
            assert error_dict["error"] == "NOT_FOUND_ERROR"
            assert error_dict["message"] == context.message
            assert error_dict["status_code"] == 404
            assert error_dict["details"] == context.details


class TestExternalServiceError:
    def test_creates_with_service_failure_details(self):
        with given([prepare_service_error_details()]) as context:
            exception = ExternalServiceError(message=context.message, details=context.details)

        with when("creating external service error"):
            error_dict = exception.to_dict()

        with then("should contain service failure details"):
            assert error_dict["error"] == "EXTERNAL_SERVICE_ERROR"
            assert error_dict["message"] == context.message
            assert error_dict["status_code"] == 502
            assert error_dict["details"] == context.details


class TestBusinessLogicError:
    def test_creates_with_business_rule_violation_details(self):
        with given([prepare_business_error_details()]) as context:
            exception = BusinessLogicError(message=context.message, details=context.details)

        with when("creating business logic error"):
            error_dict = exception.to_dict()

        with then("should contain business rule details"):
            assert error_dict["error"] == "BUSINESS_LOGIC_ERROR"
            assert error_dict["message"] == context.message
            assert error_dict["status_code"] == 400
            assert error_dict["details"] == context.details
