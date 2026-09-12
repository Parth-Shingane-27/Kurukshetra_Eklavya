"""Context-Aware Form Assistance (browser extension / mobile toggle feature).

Two-step session handshake, deliberately not a single long-lived token in a URL:
1. `POST /assistance/session` (called by our own frontend, when a citizen is about to open a
   scheme's verified application link) mints a short opaque `session_id`, stored server-side,
   scoped to one scheme + the application URL's own origin.
2. The extension/mobile app, running ON that application page, calls
   `POST /assistance/validate-session` with the `session_id` (read from the URL) and the page's
   OWN origin (which client-side JS cannot forge — the browser sets it). Only if the origin
   matches what was stored for that session does the server hand back a short-lived
   `assistance_token` (a JWT, distinct `typ` claim from a login access token) — that's what
   actually authorizes `explain-text` calls, and it never appears in a URL.
"""

import base64
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings


class CreateAssistanceSessionRequest(BaseModel):
    scheme_id: str


class AssistanceSessionOut(BaseModel):
    session_id: str
    application_url: str
    application_link_status: str
    expires_at: datetime


class ValidateSessionRequest(BaseModel):
    session_id: str
    origin: str
    """The requesting page's own origin (e.g. `https://pmkisan.gov.in`) — supplied by the
    extension from `window.location.origin`, never trusted as a claim the client can assert
    about someone else's origin, since it's compared against the value stored at session
    creation time, not merely echoed back."""


class ValidateSessionResponse(BaseModel):
    valid: bool
    scheme_id: str | None = None
    scheme_name: str | None = None
    assistance_token: str | None = None
    expires_at: datetime | None = None
    reason: str | None = None
    """Set when valid=False — shown as the extension's "why assistance isn't available here"
    message rather than a generic failure."""


class FormAssistanceRequest(BaseModel):
    """`scheme_id`/`page_origin` are deliberately NOT accepted here — they come only from the
    already-validated `assistance_token` bearer (see app/core/auth.py's
    `require_assistance_session`), so a client can never claim a different scheme/origin than
    the one its session was actually issued for."""

    selected_text: str | None = None
    field_label: str | None = None
    field_options: list[str] = Field(default_factory=list)
    nearby_help_text: str | None = None
    preferred_language: str | None = None
    explanation_mode: Literal["text", "voice", "text_and_voice"] = "text"


class FormAssistanceScreenshotRequest(BaseModel):
    """The screenshot-crop counterpart to FormAssistanceRequest (Section 7 Option B). Same
    session-derived scheme_id/origin rule applies — nothing here is trusted from the client
    beyond the image itself and display preferences.
    """

    screenshot_base64: str
    mime_type: Literal["image/png", "image/jpeg"] = "image/png"
    preferred_language: str | None = None
    explanation_mode: Literal["text", "voice", "text_and_voice"] = "text"

    @field_validator("screenshot_base64")
    @classmethod
    def _enforce_size_limit(cls, v: str) -> str:
        # Decoded size, not the base64 string length (base64 inflates size ~33%) — matches
        # what actually gets held in memory and sent to the LLM.
        try:
            decoded_len = len(base64.b64decode(v, validate=True))
        except Exception as exc:
            raise ValueError("screenshot_base64 is not valid base64") from exc
        max_bytes = get_settings().assistance_screenshot_max_bytes
        if decoded_len > max_bytes:
            raise ValueError(
                f"Screenshot is {decoded_len} bytes, which exceeds the {max_bytes}-byte limit — "
                "crop a smaller region of the form."
            )
        return v


class OptionExplanation(BaseModel):
    option: str
    meaning: str


class PolicyBasisItem(BaseModel):
    content: str
    source: Literal["dataset_provided", "curated_knowledge_base"]
    source_url: str | None = None


class FormAssistanceResponse(BaseModel):
    detected_language: str
    question_meaning: str
    option_explanations: list[OptionExplanation] = Field(default_factory=list)
    what_information_is_expected: str
    example: str | None = None
    important_caution: str | None = None
    """Populated whenever the field is eligibility-adjacent (BR-020) — e.g. "This field is one
    part of the eligibility assessment; your final eligibility may depend on other conditions."
    Never a statement that the citizen is/isn't eligible."""
    policy_basis: list[PolicyBasisItem] = Field(default_factory=list)
    confidence: float
    needs_clarification: bool
    clarification_question: str | None = None


class AssistanceFeedbackRequest(BaseModel):
    """"Report incorrect explanation" — stored for a curator to review, never auto-acted on;
    this is feedback about the assistant's OUTPUT, distinct from FR-011's Feedback/Grievance
    Agent which handles a citizen's grievance about a SCHEME/DEPARTMENT."""

    selected_text: str | None = None
    field_label: str | None = None
    explanation_given: str
    is_helpful: bool
    comment: str | None = None
