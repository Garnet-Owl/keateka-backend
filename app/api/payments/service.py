from datetime import datetime, UTC
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import Payment, PaymentStatus
from .mpesa import MPESAClient
from .schemas import PaymentCreate


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.mpesa_client = MPESAClient()

    async def create_payment(self, payment_data: PaymentCreate, user_id: int, reference: str) -> Payment:
        """Create a new payment record"""
        payment_dict = payment_data.model_dump()
        payment = Payment(
            reference=reference,
            user_id=user_id,
            created_at=datetime.now(UTC),
            **payment_dict,
        )

        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    async def get_payment(self, payment_id: int) -> Optional[Payment]:
        """Get payment by ID"""
        query = (
            select(Payment)
            .options(selectinload(Payment.job), selectinload(Payment.user))
            .where(Payment.id == payment_id)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_payment_by_reference(self, reference: str) -> Optional[Payment]:
        """Get payment by reference number"""
        query = select(Payment).where(Payment.reference == reference)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_payment_by_checkout_request_id(self, checkout_request_id: str) -> Optional[Payment]:
        """Get payment by M-PESA checkout request ID"""
        query = select(Payment).where(Payment.provider_metadata["CheckoutRequestID"].astext == checkout_request_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_payments(
        self,
        user_id: Optional[int] = None,
        job_id: Optional[int] = None,
        status: Optional[PaymentStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Payment]:
        """List payments with optional filters"""
        query = select(Payment).options(selectinload(Payment.job), selectinload(Payment.user))

        if user_id:
            query = query.where(Payment.user_id == user_id)
        if job_id:
            query = query.where(Payment.job_id == job_id)
        if status:
            query = query.where(Payment.status == status)

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def initiate_mpesa_payment(self, payment: Payment, phone_number: str) -> dict:
        """Initiate M-PESA payment"""
        try:
            response = await self.mpesa_client.initiate_stk_push(payment, phone_number)

            # Validate response
            if not response.get("CheckoutRequestID"):
                raise ValueError("Invalid M-PESA response: missing CheckoutRequestID")

            # Update payment with M-PESA checkout request ID
            payment.status = PaymentStatus.PROCESSING
            payment.provider_metadata = {
                "CheckoutRequestID": response["CheckoutRequestID"],
                "MerchantRequestID": response["MerchantRequestID"],
            }
            payment.updated_at = datetime.now(UTC)

            await self.db.commit()
            await self.db.refresh(payment)

            return response
        except Exception as e:
            payment.status = PaymentStatus.FAILED
            payment.updated_at = datetime.now(UTC)
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to initiate M-PESA payment: {str(e)}",
            )

    async def update_payment_status(
        self,
        payment: Payment,
        new_status: PaymentStatus,
        provider_reference: Optional[str] = None,
        provider_metadata: Optional[Dict[str, Any]] = None,
    ) -> Payment:
        """Update payment status"""
        payment.status = new_status
        payment.updated_at = datetime.now(UTC)

        if provider_reference:
            payment.provider_reference = provider_reference

        if provider_metadata:
            if not payment.provider_metadata:
                payment.provider_metadata = {}
            payment.provider_metadata.update(provider_metadata)

        if new_status in [PaymentStatus.COMPLETED, PaymentStatus.FAILED]:
            payment.completed_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(payment)
        return payment
