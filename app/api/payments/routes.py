from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth.dependencies import get_current_user
from app.api.jobs.service import JobService
from app.api.payments import schemas
from app.api.payments.core import PaymentProcessor
from app.api.payments.models import PaymentStatus
from app.api.payments.service import PaymentService
from app.api.payments.dependencies import get_payment_service, get_payment_processor, get_job_service
from app.api.shared.utils.time import TimeUtils

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("/mpesa/initiate", response_model=schemas.PaymentResponse)
async def initiate_mpesa_payment(
    payment_data: schemas.MPESAPaymentCreate,
    payment_service: PaymentService = Depends(get_payment_service),
    payment_processor: PaymentProcessor = Depends(get_payment_processor),
    job_service: JobService = Depends(get_job_service),
    current_user=Depends(get_current_user),
):
    """Initiate M-PESA payment."""
    # Verify job exists and user has permission to pay
    job = await job_service.get_job(payment_data.job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {payment_data.job_id} not found")
    if job.client_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to make payment for this job")

    # Create initial payment record
    payment = await payment_service.create_payment(
        payment_data=payment_data, user_id=current_user.id, reference=f"PAY-{job.id}-{TimeUtils.generate_timestamp()}"
    )

    # Process M-PESA payment
    try:
        return await payment_processor.process_mpesa_payment(payment=payment, phone_number=payment_data.phone_number)
    except Exception as e:
        # Ensure payment is marked as failed
        await payment_service.update_payment_status(payment, PaymentStatus.FAILED, provider_metadata={"error": str(e)})
        raise


@router.get("/{payment_id}", response_model=schemas.PaymentResponse)
async def get_payment(
    payment_id: int,
    payment_service: PaymentService = Depends(get_payment_service),
    current_user=Depends(get_current_user),
):
    """Get payment details."""
    payment = await payment_service.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Payment {payment_id} not found")

    # Verify user has permission to view payment
    if payment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this payment")

    return payment


@router.get("/", response_model=List[schemas.PaymentResponse])
async def list_payments(
    job_id: int = None,
    status: PaymentStatus = None,
    skip: int = 0,
    limit: int = 50,
    payment_service: PaymentService = Depends(get_payment_service),
    current_user=Depends(get_current_user),
):
    """List user's payments."""
    return await payment_service.list_payments(
        user_id=current_user.id, job_id=job_id, status=status, skip=skip, limit=limit
    )


@router.post("/mpesa/callback")
async def mpesa_callback(callback_data: dict, payment_service: PaymentService = Depends(get_payment_service)):
    """Handle M-PESA payment callback."""
    checkout_request_id = callback_data.get("CheckoutRequestID")
    result_code = callback_data.get("ResultCode")

    if not checkout_request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing CheckoutRequestID in callback data"
        )

    # Find payment by checkout request ID
    payment = await payment_service.get_payment_by_checkout_request_id(checkout_request_id)

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with checkout request ID {checkout_request_id} not found",
        )

    if result_code == "0":
        # Payment successful
        await payment_service.update_payment_status(
            payment,
            PaymentStatus.COMPLETED,
            provider_reference=callback_data.get("TransactionId"),
            provider_metadata=callback_data,
        )
    else:
        # Payment failed
        await payment_service.update_payment_status(
            payment,
            PaymentStatus.FAILED,
            provider_metadata={**callback_data, "error": callback_data.get("ResultDesc", "Payment failed")},
        )

    return {"status": "success"}
