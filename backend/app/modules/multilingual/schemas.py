from pydantic import BaseModel


class DetectAndTranslate(BaseModel):
    """Structured-output schema for the incoming-message step (Section 7.4, step 1-2)."""

    detected_language: str
    translated_text: str
