from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.shared.database import get_db
from app.api.jobs.service import JobService
from app.api.payments.mpesa import MPESAClient
from app.api.payments.service import PaymentService
from app.api.payments.core import PaymentProcessor


async def get_payment_service(db: AsyncSession = Depends(get_db)) -> PaymentService:
    """Get PaymentService instance."""
    return PaymentService(db)


async def get_mpesa_client() -> MPESAClient:
    """Get MPESAClient instance."""
    return MPESAClient()


async def get_job_service(db: AsyncSession = Depends(get_db)) -> JobService:
    """Get JobService instance."""
    return JobService(db)


async def get_payment_processor(
    payment_service: PaymentService = Depends(get_payment_service),
    mpesa_client: MPESAClient = Depends(get_mpesa_client),
) -> PaymentProcessor:
    """Get PaymentProcessor instance."""
    return PaymentProcessor(payment_service, mpesa_client)
