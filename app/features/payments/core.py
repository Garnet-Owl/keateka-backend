from typing import Optional

from app.features.payments.models import Payment, PaymentStatus
from app.features.payments.exceptions import PaymentProcessingError, InvalidPaymentStateError
from app.features.payments.mpesa import MPESAClient
from app.features.payments.service import PaymentService


class PaymentProcessor:
    def __init__(self, payment_service: PaymentService, mpesa_client: Optional[MPESAClient] = None):
        self.payment_service = payment_service
        self.mpesa_client = mpesa_client or MPESAClient()

    async def process_mpesa_payment(self, payment: Payment, phone_number: str) -> Payment:
        """Process M-PESA payment."""
        if payment.status != PaymentStatus.PENDING:
            raise InvalidPaymentStateError(payment.id, payment.status, PaymentStatus.PENDING)

        try:
            # Initiate STK Push
            mpesa_response = await self.mpesa_client.initiate_stk_push(payment, phone_number)

            # Update payment with M-PESA checkout request ID
            updated_payment = await self.payment_service.update_payment_status(
                payment=payment,
                new_status=PaymentStatus.PROCESSING,
                provider_metadata={
                    "CheckoutRequestID": mpesa_response["CheckoutRequestID"],
                    "MerchantRequestID": mpesa_response["MerchantRequestID"],
                },
            )
            return updated_payment

        except Exception as e:
            await self.payment_service.update_payment_status(payment=payment, new_status=PaymentStatus.FAILED)
            raise PaymentProcessingError(f"Failed to process M-PESA payment: {str(e)}")
