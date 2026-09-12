"""FR-012 — Multilingual Conversational & Voice Profile Intake.

`ExtractedProfileSlots` deliberately mirrors `CitizenBase`'s own field names/shape (Section 13,
FR-001) field-for-field — this is what lets every extracted value be re-validated by the
identical `CitizenUpdate`/`CitizenCreate` Pydantic models the structured form already uses
(BR-013), rather than a second, parallel validator that could silently drift from the real
rules. `date_of_birth` is typed as a string here (not `date`) only because that's what a
structured LLM tool-call can produce; it still gets parsed/validated as a real `date` the
moment it's handed to `CitizenUpdate`.
"""

from typing import Any

from pydantic import BaseModel


class ExtractedProfileSlots(BaseModel):
    name: str | None = None
    date_of_birth: str | None = None
    state: str | None = None
    district: str | None = None
    gender: str | None = None
    annual_income: float | None = None
    occupation: str | None = None
    social_category: str | None = None
    disability_status: bool | None = None
    land_holding_acres: float | None = None
    family_size: int | None = None
    marital_status: str | None = None
    bpl_status: bool | None = None
    education_level: str | None = None
    employment_status: str | None = None


class SlotExtractionDraft(BaseModel):
    """LLM structured-output schema for one conversational-intake turn."""

    extracted: ExtractedProfileSlots
    follow_up_question_en: str | None = None
    """The next question to ask, in English — translated back to the citizen's own language
    before it's returned (Section 7.4's Multi-language Chat Agent, reused). None only when the
    model considers every mandatory slot already collected."""


class ConverseRequest(BaseModel):
    transcript: str
    session_id: str | None = None
    """None starts a new conversation; pass the session_id from the previous turn's response to
    continue an in-progress one."""
    target_language: str | None = None
    """Explicit language code (en/hi/mr) for the reply; None auto-detects from `transcript`
    (Q-007: this implementation defaults to auto-detect per utterance rather than requiring an
    upfront language selection, but an explicit value always wins)."""


class ConverseResponse(BaseModel):
    session_id: str
    detected_language: str
    collected_profile: dict[str, Any]
    rejected_fields: dict[str, str]
    """field_name -> the exact validation error `CitizenUpdate` raised for it (BR-013) — a
    value that fails validation is surfaced, never silently dropped or silently accepted."""
    assistant_message: str
    is_complete: bool
    citizen_id: str | None = None
    """Set once all mandatory fields (name, date_of_birth, state, district) validate — the
    profile is created via the same `profile.service.create_citizen` path FR-001's structured
    form uses, and proceeds into FR-004 exactly as a form-submitted profile would."""
