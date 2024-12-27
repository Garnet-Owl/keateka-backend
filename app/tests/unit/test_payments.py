import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.payments.core import PaymentProcessor
from app.api.payments.service import PaymentService
from app.api.payments.mpesa import MPESAClient
from app.api.payments.models import Payment, PaymentStatus, PaymentProvider
from app.api.payments.exceptions import (
    PaymentProcessingError,
    InvalidPaymentStateError,
)
from app.api.payments.schemas import PaymentCreate, MPESAPaymentCreate
from app.tests.givenpy import given, when, then


def prepare_db():
    def step(context):
        context.db = AsyncMock(spec=AsyncSession)
        context.db.execute = AsyncMock()
        context.db.commit = AsyncMock()
        context.db.refresh = AsyncMock()
        context.db.add = AsyncMock()
        return context

    return step


def prepare_test_payment():
    def step(context):
        test_amount = 1000.00
        # Regular payment create data
        context.test_payment_data = PaymentCreate(
            amount=test_amount, job_id=1, provider=PaymentProvider.MPESA, currency="KES"
        )

        # M-PESA specific payment data
        context.test_mpesa_payment_data = MPESAPaymentCreate(
            amount=test_amount,
            job_id=1,
            provider=PaymentProvider.MPESA,
            currency="KES",
            phone_number="254712345678",
        )

        # Test payment model instance
        context.test_payment = Payment(
            id=1,
            reference="TEST123",
            amount=test_amount,
            job_id=1,
            user_id=1,
            provider=PaymentProvider.MPESA,
            currency="KES",
            status=PaymentStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        return context

    return step


def prepare_mpesa_client():
    def step(context):
        context.mpesa_client = Mock(spec=MPESAClient)
        context.mpesa_client.initiate_stk_push = AsyncMock()
        context.mpesa_client.check_transaction_status = AsyncMock()
        return context

    return step


def assert_float_equal(actual: float, expected: float, tolerance: float = 0.001) -> bool:
    """Assert that two float values are equal within a tolerance."""
    return abs(actual - expected) <= tolerance


class TestPaymentService:
    @pytest.mark.asyncio
    async def test_create_payment_succeeds(self):
        """Test successful payment creation."""
        with given([prepare_db(), prepare_test_payment()]) as context:
            payment_service = PaymentService(context.db)
            context.db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=None)

            with when("creating a new payment"):
                payment = await payment_service.create_payment(
                    context.test_payment_data, user_id=1, reference="TEST123"
                )

            with then("payment should be created successfully"):
                assert payment is not None
                assert assert_float_equal(payment.amount, context.test_payment_data.amount)
                assert payment.status == PaymentStatus.PENDING
                assert payment.provider == PaymentProvider.MPESA
                context.db.add.assert_called_once()
                await context.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_payment_by_reference_returns_payment(self):
        """Test retrieving payment by reference."""
        with given([prepare_db(), prepare_test_payment()]) as context:
            payment_service = PaymentService(context.db)
            context.db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=context.test_payment)

            with when("getting payment by reference"):
                payment = await payment_service.get_payment_by_reference("TEST123")

            with then("should return the payment"):
                assert payment is not None
                assert payment.reference == "TEST123"
                assert assert_float_equal(payment.amount, 1000.00)
                assert payment.provider == PaymentProvider.MPESA

    @pytest.mark.asyncio
    async def test_update_payment_status_succeeds(self):
        """Test payment status update."""
        with given([prepare_db(), prepare_test_payment()]) as context:
            payment_service = PaymentService(context.db)

            with when("updating payment status"):
                updated_payment = await payment_service.update_payment_status(
                    payment=context.test_payment,
                    new_status=PaymentStatus.COMPLETED,
                    provider_reference="MPESA123",
                    provider_metadata={"transaction_id": "TRX123"},
                )

            with then("payment should be updated correctly"):
                assert updated_payment.status == PaymentStatus.COMPLETED
                assert updated_payment.provider_reference == "MPESA123"
                assert updated_payment.provider_metadata["transaction_id"] == "TRX123"
                assert updated_payment.completed_at is not None
                await context.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_payments_with_filters(self):
        """Test listing payments with filters."""
        with given([prepare_db(), prepare_test_payment()]) as context:
            payment_service = PaymentService(context.db)
            context.db.execute.return_value.scalars.return_value.all = AsyncMock(return_value=[context.test_payment])

            with when("listing payments with filters"):
                payments = await payment_service.list_payments(user_id=1, job_id=1, status=PaymentStatus.PENDING)

            with then("should return filtered payments"):
                assert len(payments) == 1
                assert payments[0].user_id == 1
                assert payments[0].job_id == 1
                assert payments[0].status == PaymentStatus.PENDING
                assert payments[0].provider == PaymentProvider.MPESA
                assert assert_float_equal(payments[0].amount, context.test_payment.amount)


class TestPaymentProcessor:
    @pytest.mark.asyncio
    async def test_process_mpesa_payment_succeeds(self):
        """Test successful M-PESA payment processing."""
        with given([prepare_db(), prepare_test_payment(), prepare_mpesa_client()]) as context:
            payment_service = PaymentService(context.db)
            payment_processor = PaymentProcessor(payment_service, context.mpesa_client)

            # Mock successful M-PESA response
            context.mpesa_client.initiate_stk_push.return_value = {
                "CheckoutRequestID": "ws_CO_123456789",
                "MerchantRequestID": "123456",
                "ResponseCode": "0",
                "ResponseDescription": "Success",
            }

            with when("processing M-PESA payment"):
                result = await payment_processor.process_mpesa_payment(
                    context.test_payment, phone_number="254712345678"
                )

            with then("payment should be processed successfully"):
                assert result is not None
                context.mpesa_client.initiate_stk_push.assert_called_once()
                assert context.test_payment.status == PaymentStatus.PROCESSING

    @pytest.mark.asyncio
    async def test_process_mpesa_payment_invalid_state_fails(self):
        """Test M-PESA payment processing fails with invalid payment state."""
        with given([prepare_db(), prepare_test_payment(), prepare_mpesa_client()]) as context:
            payment_service = PaymentService(context.db)
            payment_processor = PaymentProcessor(payment_service, context.mpesa_client)
            context.test_payment.status = PaymentStatus.PROCESSING

            with (
                when("processing payment in invalid state"),
                pytest.raises(InvalidPaymentStateError) as exc_info,
            ):
                await payment_processor.process_mpesa_payment(context.test_payment, phone_number="254712345678")

            with then("should raise invalid state error"):
                assert "Invalid payment state" in str(exc_info.value)


class TestMPESAClient:
    @pytest.mark.asyncio
    async def test_initiate_stk_push_succeeds(self):
        """Test successful STK push initiation."""
        with given([prepare_test_payment()]) as context:
            with patch("httpx.AsyncClient") as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "CheckoutRequestID": "ws_CO_123456789",
                    "MerchantRequestID": "123456",
                    "ResponseCode": "0",
                    "ResponseDescription": "Success",
                }
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

                mpesa_client = MPESAClient()

                with when("initiating STK push"):
                    result = await mpesa_client.initiate_stk_push(context.test_payment, phone_number="254712345678")

                with then("should return successful response"):
                    assert result["CheckoutRequestID"] == "ws_CO_123456789"
                    assert result["ResponseCode"] == "0"

    @pytest.mark.asyncio
    async def test_check_transaction_status_succeeds(self):
        """Test successful transaction status check."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "ResultCode": "0",
                "ResultDesc": "The service request has been accepted successsfully",
                "CheckoutRequestID": "ws_CO_123456789",
            }
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            mpesa_client = MPESAClient()

            with when("checking transaction status"):
                result = await mpesa_client.check_transaction_status("ws_CO_123456789")

            with then("should return transaction status"):
                assert result["ResultCode"] == "0"
                assert "ResultDesc" in result

    @pytest.mark.asyncio
    async def test_mpesa_api_error_handling(self):
        """Test M-PESA API error handling."""
        with given([prepare_test_payment()]) as context:
            with patch("httpx.AsyncClient") as mock_client:
                mock_response = Mock()
                mock_response.status_code = 400
                mock_response.text = "Invalid request"
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

                mpesa_client = MPESAClient()

                with (
                    when("making API call that fails"),
                    pytest.raises(PaymentProcessingError) as exc_info,
                ):
                    await mpesa_client.initiate_stk_push(context.test_payment, phone_number="254712345678")

                with then("should handle error appropriately"):
                    assert "STK push request failed" in str(exc_info.value)


# Additional test cases that could be added:
# 1. Test payment expiry handling
# 2. Test concurrent payment processing
# 3. Test callback handling
# 4. Test payment refund process
# 5. Test payment reconciliation
# 6. Test payment receipt generation
# 7. Test payment notification system
# 8. Test payment retry mechanism
