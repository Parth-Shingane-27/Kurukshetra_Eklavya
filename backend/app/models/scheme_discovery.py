"""New-scheme discovery via live web search — the counterpart to rag_candidate.py, but for
schemes that don't exist in the catalogue yet instead of updates to ones that do. Same
architectural boundary: a discovery is a *proposal* only, written to `scheme_discoveries` —
never to the live `schemes` collection. Only `approve_discovery` ever writes to `schemes`, and
it does so through the existing FR-011 `create_scheme` path, the same one an admin's manual
"add scheme" form uses, so there is exactly one code path that creates a scheme.

A discovered `application_url` is never proposed as 'verified' — see
`app.models.scheme.LinkVerificationStatus` for why that status is reserved for a human who
actually checked the destination page.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.models.rag_candidate import RagSourcePassage


class SchemeDiscoveryStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class DiscoveredSchemeLinks(BaseModel):
    official_scheme_url: str | None = None
    application_url: str | None = None
    source_url: str | None = None


class DiscoveredSchemeDraft(BaseModel):
    """LLM structured-output schema for one scheme drafted from live web search text. Only
    fields the model was confident enough to ground in the retrieved text are ever non-None —
    never a guessed benefit amount or category."""

    name: str
    description: str | None = None
    issuing_authority: str | None = None
    category: str | None = None
    benefit_type: str | None = None
    benefit_value_estimate: float | None = None
    document_requirements: list[str] | None = None
    links: DiscoveredSchemeLinks = Field(default_factory=DiscoveredSchemeLinks)


class SchemeDiscoveryDraftList(BaseModel):
    """Top-level structured-output schema — one search can surface more than one distinct
    scheme (or none, if nothing found was a real, distinct government scheme)."""

    schemes: list[DiscoveredSchemeDraft]


class SchemeDiscoveryOut(BaseModel):
    id: str
    query: str
    draft: dict
    source_passages: list[RagSourcePassage]
    confidence: float
    rationale: str
    status: SchemeDiscoveryStatus
    created_at: datetime
    reviewed_at: datetime | None = None
    rejection_reason: str | None = None


class SchemeDiscoverySearchRequest(BaseModel):
    query: str
    category: str | None = None

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query must not be blank")
        return v


class SchemeDiscoveryRejectRequest(BaseModel):
    reason: str | None = None
