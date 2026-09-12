"""FR-015 — RAG-Based Knowledge Base Freshness. These types exist ONLY to move a
retrieval+drafting result into `rag_candidate_updates` for curator review (BR-015) — none of
them are ever written to the live `schemes` collection directly; only an explicit curator
approval action (via the existing FR-011 `update_scheme` path) commits anything.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class RagCandidateStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class RagProposedChanges(BaseModel):
    """A targeted diff, not a full scheme replacement — only fields the LLM was confident
    enough to ground in retrieved text are ever non-None. `criteria_summary` maps to the
    scheme's free-text `description` on approval, never to `rules` (Section 16: AI never
    writes the structured, eligibility-determining data; only a curator does, through FR-011).
    `deadline_text` has no dedicated field on `Scheme` yet — it is recorded for curator context
    but not committed anywhere structured on approval, rather than inventing a new field."""

    benefit_value_estimate: float | None = None
    criteria_summary: str | None = None
    document_requirements: list[str] | None = None
    deadline_text: str | None = None
    application_url: str | None = None


class RagCandidateDraft(BaseModel):
    """LLM structured-output schema for one drafting pass (app/graph or app/modules
    rag_refresh service uses `llm.with_structured_output(RagCandidateDraft)`)."""

    proposed_changes: RagProposedChanges
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


class RagSourcePassage(BaseModel):
    content: str
    source_url: str | None = None


class RagCandidateOut(BaseModel):
    id: str
    scheme_id: str
    scheme_name: str
    status: RagCandidateStatus
    proposed_changes: dict
    current_snapshot: dict
    source_passages: list[RagSourcePassage]
    confidence: float
    rationale: str
    created_at: datetime
    reviewed_at: datetime | None = None
    rejection_reason: str | None = None


class RagCandidateRejectRequest(BaseModel):
    reason: str | None = None
