from pydantic import BaseModel, Field


class DetectAndTranslateRequest(BaseModel):
    text: str


class DetectAndTranslateOut(BaseModel):
    detected_language: str
    translated_text: str


class TranslateResponseRequest(BaseModel):
    text: str
    target_language: str
    critical_values: list[str] = Field(default_factory=list)
    """Scheme names, amounts, dates, document names already computed elsewhere in the
    pipeline — the translation is rejected (falls back to English) if any of these don't
    survive verbatim (Section 7.4)."""


class TranslateResponseOut(BaseModel):
    text: str
    translated: bool
    warning: str | None
