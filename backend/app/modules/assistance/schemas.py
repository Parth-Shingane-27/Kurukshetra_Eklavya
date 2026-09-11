from pydantic import BaseModel, Field

from app.models.assistance import OptionExplanation


class FormExplanationDraft(BaseModel):
    """What the LLM itself is asked to produce — deliberately narrower than
    FormAssistanceResponse: `detected_language` and `policy_basis` are populated by Python
    from already-computed state, never left for the model to assert on its own."""

    question_meaning: str
    option_explanations: list[OptionExplanation] = Field(default_factory=list)
    what_information_is_expected: str
    example: str | None = None
    important_caution: str | None = None
    needs_clarification: bool = False
    clarification_question: str | None = None
    confidence: float = 0.7
