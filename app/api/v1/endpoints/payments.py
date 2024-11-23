from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from app.core.deps import get_current_user
from app.database import get_db
from app.models.job import Job, JobStatus, PaymentStatus
from app.models.user import User
from app.schemas.payment import (
    PaymentCreate,
    PaymentResponse,
    PaymentCallback,
    PaymentStatusResponse,
)
from app.services.mpesa import initiate_payment
from app.core.notifications import send_notification

router = APIRouter()


@router.post("/initiate", response_model=PaymentResponse)
async def initiate_job_payment(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    payment_in: PaymentCreate,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    Initiate M-PESA payment for a job
    """
    # Get job details
    job = (
        db.query(Job)
        .filter(
            Job.id == payment_in.job_id,
            Job.client_id == current_user.id,
            Job.status == JobStatus.ACCEPTED,
        )
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or not in correct state for payment",
        )

    if job.payment_status != PaymentStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payment status: {job.payment_status}",
        )

    try:
        # Format phone number (ensure it's in the format: 254XXXXXXXXX)
        phone = current_user.phone_number
        if phone.startswith("+"):
            phone = phone[1:]
        if not phone.startswith("254"):
            phone = "254" + phone[1:] if phone.startswith("0") else phone

        # Initiate payment
        payment_response = initiate_payment(
            phone_number=phone,
            amount=int(job.total_amount),  # Convert to integer (cents)
            reference=f"JOB#{job.id}",
            description=f"Payment for cleaning service: {job.title}",
        )

        # Update job with payment reference
        job.mpesa_reference = payment_response.get("CheckoutRequestID")
        db.commit()

        # Schedule status check
        background_tasks.add_task(
            check_payment_status,
            db=db,
            job_id=job.id,
            checkout_request_id=job.mpesa_reference,
        )

        return {
            "message": "Payment initiated successfully",
            "status": "pending",
            "checkout_request_id": job.mpesa_reference,
            **payment_response,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment initiation failed: {str(e)}",
        )


@router.post("/callback", response_model=Dict[str, str])
async def handle_payment_callback(
    *, db: Session = Depends(get_db), callback_data: PaymentCallback
) -> Dict[str, str]:
    """
    Handle M-PESA payment callback
    """
    checkout_request_id = callback_data.CheckoutRequestID
    result_code = callback_data.ResultCode
    result_desc = callback_data.ResultDesc

    # Find job by checkout request ID
    job = (
        db.query(Job)
        .filter(Job.mpesa_reference == checkout_request_id)
        .first()
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found for this payment reference",
        )

    # Update payment status based on result
    if result_code == 0:  # Success
        job.payment_status = PaymentStatus.PAID
        # Notify users
        send_notification(
            user_id=job.client_id,
            title="Payment Successful",
            body=f"Your payment for job #{job.id} has been received",
        )
        send_notification(
            user_id=job.cleaner_id,
            title="Payment Received",
            body=f"Payment for job #{job.id} has been confirmed",
        )
    else:
        job.payment_status = PaymentStatus.FAILED
        send_notification(
            user_id=job.client_id,
            title="Payment Failed",
            body=f"Payment for job #{job.id} failed: {result_desc}",
        )

    db.commit()

    return {"status": "success", "message": "Callback processed successfully"}


@router.get("/{job_id}/status", response_model=PaymentStatusResponse)
async def get_payment_status(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get payment status for a job
    """
    job = (
        db.query(Job)
        .filter(
            Job.id == job_id,
            (Job.client_id == current_user.id)
            | (Job.cleaner_id == current_user.id),
        )
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    return {
        "job_id": job.id,
        "status": job.payment_status,
        "mpesa_reference": job.mpesa_reference,
        "amount": job.total_amount,
    }


async def check_payment_status(
    db: Session, job_id: int, checkout_request_id: str
) -> None:
    """Background task to check payment status"""
    # TODO: Implement M-PESA query API to check status
    # For now, we'll rely on the callback
    pass
