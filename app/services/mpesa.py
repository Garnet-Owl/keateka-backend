from datetime import datetime
import base64
import requests
from typing import Dict, Any
from app.core.config import settings


class MPESAClient:
    """
    M-PESA Integration Client
    """

    def __init__(self):
        self.business_shortcode = settings.MPESA_SHORTCODE
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY

        # API endpoints
        self.env = "sandbox" if settings.MPESA_ENVIRONMENT == "sandbox" else "api"
        self.base_url = f"https://{self.env}.safaricom.co.ke"
        self.token_url = (
            f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        )
        self.stk_push_url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        self.query_url = f"{self.base_url}/mpesa/stkpushquery/v1/query"

    def _get_auth_token(self) -> str:
        """Get OAuth token."""
        try:
            auth_string = base64.b64encode(
                f"{self.consumer_key}:{self.consumer_secret}".encode("utf-8")
            ).decode("utf-8")

            headers = {"Authorization": f"Basic {auth_string}"}

            response = requests.get(self.token_url, headers=headers)
            response.raise_for_status()

            result = response.json()
            return result.get("access_token")

        except Exception as e:
            print(f"Error getting auth token: {str(e)}")
            raise

    def _get_password(self, timestamp: str) -> str:
        """Generate password for STK Push."""
        data_to_encode = f"{self.business_shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(data_to_encode.encode("utf-8")).decode("utf-8")


def initiate_payment(
    phone_number: str, amount: int, reference: str, description: str
) -> Dict[str, Any]:
    """
    Initiate M-PESA STK Push payment

    Args:
        phone_number: Customer phone number (format: 254XXXXXXXXX)
        amount: Amount to charge
        reference: Transaction reference
        description: Transaction description

    Returns:
        Dict containing M-PESA response
    """
    try:
        client = MPESAClient()
        access_token = client._get_auth_token()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = client._get_password(timestamp)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "BusinessShortCode": client.business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": client.business_shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": f"{settings.API_V1_STR}/payments/callback",
            "AccountReference": reference,
            "TransactionDesc": description,
        }

        response = requests.post(client.stk_push_url, headers=headers, json=payload)
        response.raise_for_status()

        return response.json()

    except Exception as e:
        print(f"Error initiating payment: {str(e)}")
        raise
