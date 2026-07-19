from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.exceptions import BadRequestError


class EmailService:
    """Thin async adapter around Resend's email API."""

    async def send_email_verification(self, *, to_email: str, full_name: str, otp_code: str, verification_token: str) -> None:
        verify_url = None
        if settings.FRONTEND_EMAIL_VERIFY_URL:
            verify_url = f"{settings.FRONTEND_EMAIL_VERIFY_URL.rstrip('/')}?token={verification_token}&email={to_email}"
        html = self._verification_html(full_name=full_name, otp_code=otp_code, verify_url=verify_url)
        await self._send(to_email=to_email, subject="Verify your ProHub email", html=html)

    async def _send(self, *, to_email: str, subject: str, html: str) -> None:
        if not settings.RESEND_API_KEY:
            if settings.ENVIRONMENT == "production":
                raise BadRequestError("Resend API key is not configured")
            return
        payload = {"from": settings.EMAIL_FROM, "to": [to_email], "subject": subject, "html": html}
        headers = {"Authorization": f"Bearer {settings.RESEND_API_KEY}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post("https://api.resend.com/emails", json=payload, headers=headers)
        if response.status_code >= 400:
            raise BadRequestError("Email delivery failed", details=response.text)

    @staticmethod
    def _verification_html(*, full_name: str, otp_code: str, verify_url: str | None) -> str:
        link = f'<p><a href="{verify_url}">Verify your email</a></p>' if verify_url else ""
        return f"""
        <div style="font-family:Arial,sans-serif;line-height:1.6;color:#111827">
          <h2>Verify your email</h2>
          <p>Hello {full_name},</p>
          <p>Use this verification code to activate your ProHub account:</p>
          <p style="font-size:28px;font-weight:700;letter-spacing:4px">{otp_code}</p>
          {link}
          <p>This code expires shortly. Ignore this email if you did not create a ProHub account.</p>
        </div>
        """
