"""Citizen-reported data-quality issues on a scheme (Section 21's "report incorrect
information"). Deliberately distinct from FR-015's RAG candidate queue — a report here is a
raw citizen claim, not an AI-drafted, source-grounded proposal; it never auto-updates
`schemes`, it only queues something for a curator to look into (and, if warranted, the curator
acts through the existing FR-011 edit path or triggers a FR-015 RAG refresh — this collection
itself never writes to `schemes`)."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, field_validator

ReportReason = str  # free-text category chosen from a small fixed frontend list; not an enum
# server-side so a new reason category never needs a backend deploy to add.


class SchemeReportStatus(str, Enum):
    open = "open"
    dismissed = "dismissed"
    addressed = "addressed"


class SchemeReportCreate(BaseModel):
    scheme_id: str
    reason: str
    comment: str | None = None
    citizen_id: str | None = None
    """Optional — a report can come from an anonymous catalog browser with no profile."""

    @field_validator("reason")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v


class SchemeReportOut(BaseModel):
    id: str
    scheme_id: str
    scheme_name: str
    reason: str
    comment: str | None
    citizen_id: str | None
    status: SchemeReportStatus
    admin_notes: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime


class ResolveSchemeReportRequest(BaseModel):
    status: SchemeReportStatus
    admin_notes: str | None = None

    @field_validator("status")
    @classmethod
    def must_be_terminal(cls, v: SchemeReportStatus) -> SchemeReportStatus:
        if v == SchemeReportStatus.open:
            raise ValueError("Resolving a report must set it to 'dismissed' or 'addressed', not 'open'")
        return v
