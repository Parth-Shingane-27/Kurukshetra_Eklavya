from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRole(str, Enum):
    citizen = "citizen"
    admin = "admin"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole = UserRole.citizen
    admin_bootstrap_credential: str | None = None
    """Required and checked only when role == admin (Section 20) — prevents open self-service
    admin signup; reuses the existing shared ADMIN_CREDENTIAL as the one-time bootstrap secret."""

    @field_validator("password")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("password must not be blank")
        return v


class UserOut(BaseModel):
    id: str
    email: str
    role: UserRole
    citizen_id: str | None = None
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
