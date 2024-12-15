import base64
from datetime import datetime, UTC
from typing import Dict, Optional

import httpx

from app.features.payments.exceptions import PaymentProcessingError
from app.features.payments.models import Payment
from app.shared.config import get_settings
from app.shared.utils.time import TimeUtils

settings = get_settings()

# Constants
CONTENT_TYPE_JSON = "application/json"
TOKEN_EXPIRY_SECONDS = 3500  # Set slightly less than 1 hour to ensure token refresh


class MPESAClient:
    def __init__(self):
        """Initialize MPESA client with configuration."""
        self.consumer_key = settings.mpesa_consumer_key
        self.consumer_secret = settings.mpesa_consumer_secret
        self.business_shortcode = settings.mpesa_business_shortcode
        self.passkey = settings.mpesa_passkey
        self.environment = "sandbox" if settings.environment != "production" else "production"
        self.base_url = (
            "https://sandbox.safaricom.co.ke" if self.environment == "sandbox" else "https://api.safaricom.co.ke"
        )
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[float] = None
        self.timeout = httpx.Timeout(30.0)  # 30 seconds timeout

    async def _get_access_token(self) -> str:
        """
        Get OAuth access token from Safaricom.

        Returns:
            str: Access token

        Raises:
            PaymentProcessingError: If token generation fails
        """
        try:
            if self._access_token and self._token_expiry and datetime.now(UTC).timestamp() < self._token_expiry:
                return self._access_token

            credentials = f"{self.consumer_key}:{self.consumer_secret}".encode()
            auth_string = base64.b64encode(credentials).decode("ascii")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials",
                    headers={"Authorization": f"Basic {auth_string}", "Content-Type": CONTENT_TYPE_JSON},
                )

                if response.status_code != 200:
                    raise PaymentProcessingError(
                        message=f"Failed to get access token. Status: {response.status_code}",
                        details={"response": response.text},
                    )

                data = response.json()
                self._access_token = data["access_token"]
                self._token_expiry = datetime.now(UTC).timestamp() + TOKEN_EXPIRY_SECONDS
                return self._access_token

        except httpx.HTTPError as e:
            raise PaymentProcessingError(message="Network error while getting access token", details={"error": str(e)})
        except Exception as e:
            raise PaymentProcessingError(
                message="Unexpected error while getting access token", details={"error": str(e)}
            )

    def _generate_password(self, timestamp: str) -> str:
        """
        Generate the M-PESA API password using the provided timestamp.

        Args:
            timestamp (str): Timestamp in the format YYYYMMDDHHmmss

        Returns:
            str: Base64 encoded password
        """
        data_to_encode = f"{self.business_shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(data_to_encode.encode()).decode("ascii")

    async def initiate_stk_push(self, payment: Payment, phone_number: str) -> Dict:
        """
        Initiate M-PESA STK Push payment.

        Args:
            payment (Payment): Payment object with transaction details
            phone_number (str): Customer's phone number (format: 254XXXXXXXXX)

        Returns:
            Dict: M-PESA API response

        Raises:
            PaymentProcessingError: If the request fails
        """
        try:
            access_token = await self._get_access_token()
            timestamp = TimeUtils.generate_timestamp()

            # Format phone number (ensure it starts with 254)
            if phone_number.startswith("0"):
                phone_number = "254" + phone_number[1:]
            elif phone_number.startswith("+"):
                phone_number = phone_number[1:]

            payload = {
                "BusinessShortCode": self.business_shortcode,
                "Password": self._generate_password(timestamp),
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(payment.amount),
                "PartyA": phone_number,
                "PartyB": self.business_shortcode,
                "PhoneNumber": phone_number,
                "CallBackURL": f"{settings.api_base_url}/api/v1/payments/mpesa-callback",
                "AccountReference": payment.reference,
                "TransactionDesc": f"Payment for job {payment.job_id}",
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                    json=payload,
                    headers={"Authorization": f"Bearer {access_token}", "Content-Type": CONTENT_TYPE_JSON},
                )

                if response.status_code != 200:
                    raise PaymentProcessingError(
                        message="STK push request failed",
                        details={
                            "status_code": response.status_code,
                            "response": response.text,
                            "payment_id": payment.id,
                        },
                    )

                result = response.json()

                # Validate response format
                if "ResponseCode" in result and result["ResponseCode"] != "0":
                    raise PaymentProcessingError(
                        message=f"STK push request failed: {result.get('ResponseDescription', 'Unknown error')}",
                        details={"response": result, "payment_id": payment.id},
                    )

                return result

        except httpx.HTTPError as e:
            raise PaymentProcessingError(
                message="Network error during STK push request",
                details={"error": str(e), "payment_id": payment.id, "phone_number": phone_number},
            )
        except Exception as e:
            raise PaymentProcessingError(
                message=str(e), details={"payment_id": payment.id, "phone_number": phone_number}
            )

    async def check_transaction_status(self, checkout_request_id: str) -> Dict:
        """
        Check STK Push transaction status.

        Args:
            checkout_request_id (str): The CheckoutRequestID from STK push response

        Returns:
            Dict: Transaction status response

        Raises:
            PaymentProcessingError: If the status check fails
        """
        try:
            access_token = await self._get_access_token()
            timestamp = TimeUtils.generate_timestamp()

            payload = {
                "BusinessShortCode": self.business_shortcode,
                "Password": self._generate_password(timestamp),
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id,
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/mpesa/stkpushquery/v1/query",
                    json=payload,
                    headers={"Authorization": f"Bearer {access_token}", "Content-Type": CONTENT_TYPE_JSON},
                )

                if response.status_code != 200:
                    raise PaymentProcessingError(
                        message="Transaction status check failed",
                        details={
                            "status_code": response.status_code,
                            "response": response.text,
                            "checkout_request_id": checkout_request_id,
                        },
                    )

                result = response.json()

                # Handle different response formats
                if "ResultCode" in result:
                    if result["ResultCode"] != "0":
                        return {
                            "status": "FAILED",
                            "reason": result.get("ResultDesc", "Unknown error"),
                            "raw_response": result,
                        }
                    return {"status": "SUCCESS", "raw_response": result}

                return result

        except httpx.HTTPError as e:
            raise PaymentProcessingError(
                message="Network error checking transaction status",
                details={"error": str(e), "checkout_request_id": checkout_request_id},
            )
        except Exception as e:
            raise PaymentProcessingError(
                message=f"Failed to check transaction status: {str(e)}",
                details={"checkout_request_id": checkout_request_id},
            )

    async def get_account_balance(self) -> Dict:
        """
        Query account balance.

        Returns:
            Dict: Account balance response

        Raises:
            PaymentProcessingError: If the balance query fails
        """
        try:
            access_token = await self._get_access_token()

            payload = {
                "Initiator": settings.mpesa_initiator_name,
                "SecurityCredential": settings.mpesa_security_credential,
                "CommandID": "AccountBalance",
                "PartyA": self.business_shortcode,
                "IdentifierType": "4",  # Shortcode identifier type
                "Remarks": "Account balance query",
                "QueueTimeOutURL": f"{settings.api_base_url}/api/v1/payments/mpesa-timeout",
                "ResultURL": f"{settings.api_base_url}/api/v1/payments/mpesa-result",
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/mpesa/accountbalance/v1/query",
                    json=payload,
                    headers={"Authorization": f"Bearer {access_token}", "Content-Type": CONTENT_TYPE_JSON},
                )

                if response.status_code != 200:
                    raise PaymentProcessingError(
                        message="Account balance query failed",
                        details={"status_code": response.status_code, "response": response.text},
                    )

                return response.json()

        except httpx.HTTPError as e:
            raise PaymentProcessingError(message="Network error querying account balance", details={"error": str(e)})
        except Exception as e:
            raise PaymentProcessingError(message=f"Failed to check account balance: {str(e)}")
