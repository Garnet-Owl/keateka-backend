# [app/services/mpesa.py]

import base64
from datetime import datetime
from typing import Dict, Any

import requests

from app.core.config import settings


class MPESAError(Exception):
    """Base exception for M-PESA related errors"""

    pass


class MPESAClient:
    """Enhanced M-PESA Integration Client"""

    def __init__(self):
        self.business_shortcode = settings.MPESA_SHORTCODE
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY
        self.env = (
            "sandbox" if settings.MPESA_ENVIRONMENT == "sandbox" else "api"
        )
        self.base_url = f"https://{self.env}.safaricom.co.ke"

        # API endpoints
        self.token_url = (
            f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        )
        self.stk_push_url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        self.query_url = f"{self.base_url}/mpesa/stkpushquery/v1/query"

    def _get_auth_token(self) -> str:
        """Get OAuth token"""
        try:
            auth_string = base64.b64encode(
                f"{self.consumer_key}:{self.consumer_secret}".encode("utf-8")
            ).decode("utf-8")

            headers = {"Authorization": f"Basic {auth_string}"}
            response = requests.get(
                self.token_url, headers=headers, timeout=30
            )
            response.raise_for_status()

            result = response.json()
            return result.get("access_token")
        except requests.exceptions.RequestException as e:
            raise MPESAError(f"Failed to get auth token: {str(e)}")

    def _get_password(self, timestamp: str) -> str:
        """Generate password for STK Push"""
        data_to_encode = f"{self.business_shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(data_to_encode.encode("utf-8")).decode("utf-8")

    def initiate_stk_push(
        self, phone_number: str, amount: int, reference: str, description: str
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
            access_token = self._get_auth_token()
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            password = self._get_password(timestamp)

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            payload = {
                "BusinessShortCode": self.business_shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": amount,
                "PartyA": phone_number,
                "PartyB": self.business_shortcode,
                "PhoneNumber": phone_number,
                "CallBackURL": f"{settings.API_V1_STR}/payments/callback",
                "AccountReference": reference,
                "TransactionDesc": description,
            }

            response = requests.post(
                self.stk_push_url, headers=headers, json=payload, timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            raise MPESAError(f"Failed to initiate payment: {str(e)}")

    def query_payment_status(self, checkout_request_id: str) -> Dict[str, Any]:
        """
        Query the status of a payment

        Args:
            checkout_request_id: The CheckoutRequestID from STK push

        Returns:
            Dict containing status response
        """
        try:
            access_token = self._get_auth_token()
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            password = self._get_password(timestamp)

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            payload = {
                "BusinessShortCode": self.business_shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id,
            }

            response = requests.post(
                self.query_url, headers=headers, json=payload, timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            raise MPESAError(f"Failed to query payment status: {str(e)}")


# Create singleton instance
mpesa_client = MPESAClient()


def initiate_payment(
    phone_number: str, amount: int, reference: str, description: str
) -> Dict[str, Any]:
    """Wrapper function for STK push initiation"""
    return mpesa_client.initiate_stk_push(
        phone_number=phone_number,
        amount=amount,
        reference=reference,
        description=description,
    )


def check_payment_status(checkout_request_id: str) -> Dict[str, Any]:
    """Wrapper function for payment status query"""
    return mpesa_client.query_payment_status(checkout_request_id)
