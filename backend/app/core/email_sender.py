"""Sends the OTP email via Resend (https://resend.com) for FR-016's second factor.

Falls back to logging the code to the console when RESEND_API_KEY is not configured — this
keeps local development/testing/demoing possible without a real provider, matching BR-010's
established fallback pattern elsewhere in this codebase. The fallback is the ONLY time the
caller gets the OTP back in the response (`debug_otp`) — once a real key is configured, the
code only ever reaches the user via the email itself.
"""

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger("asbo.auth")

RESEND_API_URL = "https://api.resend.com/emails"


async def send_otp_email(*, to_email: str, code: str) -> bool:
    """Returns True if sent via Resend, False if it fell back to console logging.

    A Resend failure (bad/unverified sender, rate limit, network error, etc.) must never crash
    login itself — the OTP flow is the second factor, not Resend's own health check — so any
    failure here degrades to the same console/`debug_otp` fallback as a missing API key,
    matching BR-010's "external service failure never blocks the pipeline" pattern elsewhere
    in this codebase.
    """
    settings = get_settings()
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set — OTP for %s is %s (console fallback)", to_email, code)
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            response = await http_client.post(
                RESEND_API_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.resend_from_email,
                    "to": [to_email],
                    "subject": "Your ASBO verification code",
                    "html": (
                        f"<p>Your ASBO login verification code is:</p>"
                        f"<p style='font-size:24px;font-weight:bold;letter-spacing:4px'>{code}</p>"
                        f"<p>This code expires in {settings.otp_expire_seconds // 60} minutes. "
                        f"If you did not request this, you can ignore this email.</p>"
                    ),
                },
            )
            response.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        detail = getattr(exc, "response", None)
        body = detail.text if detail is not None else str(exc)
        logger.warning(
            "Resend send failed for %s (%s) — OTP is %s (console fallback)", to_email, body, code
        )
        return False
