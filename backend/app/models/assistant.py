from typing import Any

from pydantic import BaseModel, Field


class UploadedDocumentIn(BaseModel):
    document_type: str
    pdf_base64: str | None = None
    document_text: str | None = None
    declared_fields: dict[str, Any] = Field(default_factory=dict)


class GrievanceDetailsIn(BaseModel):
    category: str
    description: str


class AssistantMessageRequest(BaseModel):
    thread_id: str
    """Conversation identifier — required so a human-review interrupt (Section 9) can be
    resumed against the same LangGraph checkpoint later via /resume."""
    user_query: str
    citizen_id: str | None = None
    scheme_id: str | None = None
    uploaded_document: UploadedDocumentIn | None = None
    consent: bool | None = None
    grievance_details: GrievanceDetailsIn | None = None


class AssistantResumeRequest(BaseModel):
    thread_id: str
    decision: str
    """The human reviewer's decision (e.g. "approved", "rejected") fed back into the paused
    graph run via LangGraph's Command(resume=...)."""


class AssistantMessageResponse(BaseModel):
    detected_intent: str | None = None
    final_response: str | None = None
    human_review_required: bool = False
    interrupted: bool = False
    """True when the graph paused for human review (Section 9) — call /resume with the same
    thread_id to continue."""
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    state: dict[str, Any] = Field(default_factory=dict)
    """The relevant slices of AgentState for this run (bundle, checklist, deadline_info, etc.)
    — everything JSON-serializable except internal bookkeeping."""
