"""Quick Scheme Eligibility Checker (FR-013, BR-014) — a stateless, no-account single-scheme
check. Deliberately reuses the Rule Engine's own `evaluate_scheme` (see
app/modules/quick_checker/service.py) rather than a second eligibility implementation —
BR-014's statelessness is about *persistence*, not about re-deriving eligibility logic.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.eligibility import EligibilityReason

DISCLAIMER = (
    "This is a preliminary self-assessment based only on the details you entered here, not an "
    "official government eligibility determination. Your final eligibility may depend on other "
    "conditions this quick check does not evaluate."
)


class QuickCheckRequest(BaseModel):
    scheme_id: str
    criteria: dict[str, Any] = Field(default_factory=dict)
    """Only the fields this ONE scheme's rules actually reference — not a full Citizen profile
    (FR-013: "a single scheme and just the fields its rules reference"). Accepts `date_of_birth`
    as a convenience (age is derived the same way FR-001's structured form does) or `age`
    directly."""


class SuggestedAlternativeScheme(BaseModel):
    scheme_id: str
    scheme_name: str


class QuickCheckResponse(BaseModel):
    scheme_id: str
    scheme_name: str
    status: Literal["eligible", "not_eligible", "indeterminate"]
    reasons: list[EligibilityReason]
    application_url: str | None = None
    application_link_status: str | None = None
    official_scheme_url: str | None = None
    required_documents: list[str] = Field(default_factory=list)
    suggested_alternatives: list[SuggestedAlternativeScheme] = Field(default_factory=list)
    """Populated only when status is not_eligible — other active schemes in the same category,
    per FR-013's "suggested alternative schemes from the same category" output."""
    disclaimer: str = DISCLAIMER
