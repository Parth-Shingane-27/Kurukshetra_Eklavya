from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

VerificationStatus = Literal["verified_structurally", "incomplete", "expired", "needs_review"]


class DocumentVerifyRequest(BaseModel):
    citizen_id: str
    scheme_id: str
    document_type: str
    # Exactly one text source is expected — a PDF's text layer (extracted server-side, no
    # OCR) or already-known text/declared metadata for a non-PDF document (Section 7.1: images
    # are accepted but only user-declared fields are used, never inferred from pixels).
    pdf_base64: str | None = None
    document_text: str | None = None
    declared_fields: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def at_least_one_content_source(self) -> "DocumentVerifyRequest":
        if not self.pdf_base64 and not self.document_text and not self.declared_fields:
            raise ValueError("Provide pdf_base64, document_text, or declared_fields.")
        return self


class DocumentVerificationOut(BaseModel):
    id: str
    citizen_id: str
    scheme_id: str
    document_type: str
    status: VerificationStatus
    issues: list[str]
    human_review_required: bool
    authenticity_verified: bool
    """Always False (Section 11, rule 7) — structural checks only, never a claim of authenticity."""
    created_at: datetime
