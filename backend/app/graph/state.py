"""LangGraph state (Section 8 of the brief), trimmed to the fields this graph actually
populates. `db` is deliberately NOT a state field — Motor's AsyncIOMotorDatabase isn't
checkpoint-serializable, so it's passed per-invocation via `config["configurable"]["db"]`
(see workflow.py) instead, the same way FastAPI's `Depends(get_db)` threads it through the
REST endpoints.
"""

import operator
from typing import Annotated, Any, TypedDict


class LanguageContext(TypedDict, total=False):
    detected_language: str
    target_language: str
    translation_warning: str | None


class AgentState(TypedDict, total=False):
    user_query: str
    translated_query: str
    detected_intent: str
    citizen_id: str | None
    scheme_id: str | None
    """The scheme a CHECK_DEADLINE/SET_REMINDER/REGISTER_GRIEVANCE/CHECK_ELIGIBILITY request
    is about. The API entry point (app/api/assistant.py) sets this from a structured request
    field — this graph does not attempt to extract a scheme reference out of free text."""
    language_context: LanguageContext

    retrieved_policy_evidence: list[dict[str, Any]]
    eligibility_results: dict[str, Any] | None
    conflicts_results: dict[str, Any] | None
    bundle: dict[str, Any] | None
    checklist: dict[str, Any] | None

    uploaded_document: dict[str, Any] | None
    """{document_type, document_text, pdf_base64, declared_fields} for a VERIFY_DOCUMENT
    intent — the scheme comes from `scheme_id` above, kept consistent across intents."""
    document_verification_result: dict[str, Any] | None
    deadline_info: dict[str, Any] | None
    consent: bool | None
    """Explicit consent for SET_REMINDER (Section 7.2/11) — never assumed True."""
    grievance_details: dict[str, Any] | None
    """{category, description} for REGISTER_GRIEVANCE/SUBMIT_FEEDBACK."""
    grievance_ticket: dict[str, Any] | None
    fraud_risk_assessment: dict[str, Any] | None

    human_review_required: bool
    review_decision: str | None
    """Set only when a human reviewer resumes an interrupted run (Section 9's
    "Human Review if Needed" step)."""

    errors: Annotated[list[str], operator.add]
    warnings: Annotated[list[str], operator.add]
    final_response: str
