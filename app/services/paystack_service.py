from __future__ import annotations

import hashlib
import hmac
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import BadRequestError


class PaystackService:
    def __init__(self) -> None:
        if not settings.PAYSTACK_SECRET_KEY:
            raise BadRequestError("Paystack secret key is not configured")
        self.base_url = settings.PAYSTACK_BASE_URL.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    async def initialize_transaction(
        self,
        *,
        email: str,
        amount_minor_units: int,
        reference: str,
        currency: str,
        callback_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "email": email,
            "amount": amount_minor_units,
            "reference": reference,
            "currency": currency,
            "metadata": metadata or {},
        }
        if callback_url:
            payload["callback_url"] = callback_url

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self.base_url}/transaction/initialize", json=payload, headers=self.headers)
        return self._handle_response(response)

    async def verify_transaction(self, reference: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/transaction/verify/{reference}", headers=self.headers)
        return self._handle_response(response)

    def verify_webhook_signature(self, *, raw_body: bytes, signature: str | None) -> bool:
        if not signature:
            return False
        signing_secret = settings.PAYSTACK_WEBHOOK_SECRET or settings.PAYSTACK_SECRET_KEY
        expected = hmac.new(signing_secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def _handle_response(response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise BadRequestError("Invalid response from Paystack", details=response.text) from exc

        if response.status_code >= 400 or not data.get("status"):
            raise BadRequestError("Paystack request failed", details=data)
        return data
