"""Minimal admin-credential gate (Section 20). Deliberately not a real auth system — see
Q-002: prototype-grade only, a single shared header token compared against ADMIN_CREDENTIAL.
"""

from fastapi import Header, HTTPException

from app.core.config import get_settings


async def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not x_admin_token or x_admin_token != settings.admin_credential:
        raise HTTPException(status_code=401, detail="Invalid or missing admin credential")
