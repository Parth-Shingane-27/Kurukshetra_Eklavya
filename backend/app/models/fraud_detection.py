from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, field_validator

RiskLevel = Literal["low", "medium", "high"]


class ScreenFraudRequest(BaseModel):
    citizen_id: str
    scheme_id: str | None = None
    """When given, screens only document verifications for this scheme; otherwise screens
    every verification on file for the citizen."""


class FraudFlagOut(BaseModel):
    id: str
    citizen_id: str
    scheme_id: str | None
    risk_level: RiskLevel
    indicators: list[dict[str, Any]]
    human_review_required: bool
    """Always True once risk_level != "low" (Section 11, rule 10) — never auto-denies a
    benefit based on this result."""
    summary: str
    reviewed: bool = False
    reviewer_notes: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class ReviewFraudFlagRequest(BaseModel):
    reviewer_notes: str

    @field_validator("reviewer_notes")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v
