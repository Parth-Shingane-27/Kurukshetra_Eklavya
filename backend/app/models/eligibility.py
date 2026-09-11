from datetime import datetime
from typing import Literal

from pydantic import BaseModel

EligibilityStatus = Literal["eligible", "not_eligible", "indeterminate"]


class EvaluateRequest(BaseModel):
    citizen_id: str


class EligibilityReason(BaseModel):
    field_name: str
    message: str


class EligibilityResultOut(BaseModel):
    scheme_id: str
    scheme_name: str
    status: EligibilityStatus
    reasons: list[EligibilityReason]
    application_url: str | None = None
    application_link_status: str | None = None
    """Mirrors Scheme.links.application_link_status — the frontend must not render
    `application_url` as an official "Apply Now" destination unless this is "verified"; other
    statuses ("unverified", "not_available", "state_specific") need their own honest treatment."""


class EvaluateResponse(BaseModel):
    citizen_id: str
    evaluated_at: datetime
    results: list[EligibilityResultOut]
