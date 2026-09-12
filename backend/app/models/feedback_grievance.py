from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

GrievanceStatus = Literal["open", "resolved"]


class CreateGrievanceRequest(BaseModel):
    citizen_id: str
    category: str
    description: str
    scheme_id: str | None = None

    @field_validator("category", "description")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v


class GrievanceOut(BaseModel):
    id: str
    ticket_id: str
    citizen_id: str
    scheme_id: str | None
    category: str
    description: str
    department: str | None
    """Best-effort, from the curated scheme's issuing_authority or retrieved policy text —
    None when unavailable, never invented (Section 7.3/11, rule 6)."""
    is_official_submission: bool
    """Always False in this prototype — internal platform ticket only (Section 11, rule 8)."""
    status: GrievanceStatus
    resolution_note: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime


class ResolveGrievanceRequest(BaseModel):
    resolution_note: str

    @field_validator("resolution_note")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v
