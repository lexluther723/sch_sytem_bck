import base64
from django.utils import timezone

import requests

from django.conf import settings


class DarajaService:
    """
    Safaricom Daraja API Service
    """

    @staticmethod
    def get_base_url():
        if settings.MPESA_ENVIRONMENT.lower() == "production":
            return "https://api.safaricom.co.ke"
        return "https://sandbox.safaricom.co.ke"

    @classmethod
    def get_access_token(cls):
        """
        Generate OAuth Access Token
        """

        url = (
            f"{cls.get_base_url()}"
            "/oauth/v1/generate?grant_type=client_credentials"
        )

        response = requests.get(
            url,
            auth=(
                settings.MPESA_CONSUMER_KEY,
                settings.MPESA_CONSUMER_SECRET,
            ),
            timeout=30,
        )

        response.raise_for_status()

        return response.json()["access_token"]

    @staticmethod
    def generate_password():
        """
        Generate STK Push Password
        """

        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")

        password = base64.b64encode(
            (
                settings.MPESA_SHORTCODE
                + settings.MPESA_PASSKEY
                + timestamp
            ).encode()
        ).decode()

        return password, timestamp

    @classmethod
    def stk_push(
        cls,
        phone_number,
        amount,
        account_reference,
        transaction_desc,
    ):
        """
        Initiate STK Push
        """

        token = cls.get_access_token()

        password, timestamp = cls.generate_password()

        url = (
            f"{cls.get_base_url()}"
            "/mpesa/stkpush/v1/processrequest"
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": settings.MPESA_SHORTCODE,
            "PhoneNumber": phone_number,
            "CallBackURL": settings.MPESA_CALLBACK_URL,
            "AccountReference": account_reference,
            "TransactionDesc": transaction_desc,
        }

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30,
        )
        print("=" * 50)
        print("STATUS:", response.status_code)
        print("URL:", response.url)
        print("PAYLOAD:", payload)
        print("BODY:", response.text)
        print("=" * 50)

        response.raise_for_status()

        return response.json()

    @classmethod
    def query_stk_status(cls, checkout_request_id):
        """
        Query STK Push Status
        """

        token = cls.get_access_token()

        password, timestamp = cls.generate_password()

        url = (
            f"{cls.get_base_url()}"
            "/mpesa/stkpushquery/v1/query"
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("ResponseCode") != "0":
            raise Exception(
                data.get("errorMessage")
                or data.get("ResponseDescription")
                or "STK Push failed."
            )

        return data

