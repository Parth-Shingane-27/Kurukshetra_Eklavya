import operator
from typing import Annotated, Any, TypedDict


class FormAssistanceState(TypedDict, total=False):
    scheme_id: str
    selected_text: str | None
    field_label: str | None
    field_options: list[str]
    nearby_help_text: str | None
    screenshot_base64: str | None
    screenshot_mime_type: str | None
    preferred_language: str | None

    consolidated_text: str
    detected_language: str
    translated_text: str

    scheme: dict[str, Any] | None
    policy_evidence: list[dict[str, Any]]
    policy_verified: bool

    draft: dict[str, Any] | None
    """The LLM's raw `FormExplanationDraft` (or the BR-010-style deterministic fallback if
    the LLM is unavailable) — never returned to the client as-is; `finalize_node` still has
    to attach `policy_basis`/`detected_language` and enforce the BR-020 eligibility caution."""

    final_response: dict[str, Any] | None

    errors: Annotated[list[str], operator.add]
    warnings: Annotated[list[str], operator.add]
