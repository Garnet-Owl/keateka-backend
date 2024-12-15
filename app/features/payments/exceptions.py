from typing import Any
from app.shared.exceptions import BaseAPIException, ExternalServiceError


class PaymentProcessingError(ExternalServiceError):
    """Raised when payment processing fails."""

    def __init__(
        self,
        message: str = "Payment processing failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            details=details,
        )


class InvalidPaymentStateError(BaseAPIException):
    """Raised when attempting to process a payment in an invalid state."""

    def __init__(
        self,
        payment_id: int,
        current_status: str,
        expected_status: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        message = f"Payment {payment_id} is in status {current_status}, " f"expected {expected_status}"
        super().__init__(
            message=message,
            status_code=400,
            error_code="INVALID_PAYMENT_STATE_ERROR",
            details=details
            or {
                "payment_id": payment_id,
                "current_status": current_status,
                "expected_status": expected_status,
            },
        )


class PaymentNotFoundError(BaseAPIException):
    """Raised when a payment cannot be found."""

    def __init__(
        self,
        payment_id: int | str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=f"Payment {payment_id} not found",
            status_code=404,
            error_code="PAYMENT_NOT_FOUND_ERROR",
            details=details,
        )


class PaymentValidationError(BaseAPIException):
    """Raised when payment validation fails."""

    def __init__(
        self,
        message: str = "Payment validation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=400,
            error_code="PAYMENT_VALIDATION_ERROR",
            details=details,
        )
