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
    application_link: str | None = None


class EvaluateResponse(BaseModel):
    citizen_id: str
    evaluated_at: datetime
    results: list[EligibilityResultOut]
