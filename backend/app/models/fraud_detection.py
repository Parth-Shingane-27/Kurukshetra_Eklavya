from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

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
    created_at: datetime
