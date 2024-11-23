from typing import Optional
from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    """Schema for creating a new payment"""

    job_id: int = Field(..., gt=0)


class PaymentCallback(BaseModel):
    """Schema for M-PESA callback data"""

    MerchantRequestID: str
    CheckoutRequestID: str
    ResultCode: int
    ResultDesc: str
    Amount: Optional[float] = None
    MpesaReceiptNumber: Optional[str] = None
    TransactionDate: Optional[str] = None
    PhoneNumber: Optional[str] = None


class PaymentResponse(BaseModel):
    """Schema for payment response"""

    message: str
    status: str
    checkout_request_id: str
    merchant_request_id: Optional[str] = None
    customer_message: Optional[str] = None


class PaymentStatusResponse(BaseModel):
    """Schema for payment status check"""

    job_id: int
    status: str
    mpesa_reference: Optional[str] = None
    amount: float
