from typing import Any, Literal

from pydantic import BaseModel


class GenerateChecklistRequest(BaseModel):
    bundle_id: str


class ChecklistItemOut(BaseModel):
    document_type: str
    related_scheme_ids: list[str]
    related_scheme_names: list[str]
    status: Literal["missing", "held"]
    evidence: list[dict[str, Any]] | None = None
    """Best-effort RAG evidence for this document requirement (Section 6) — absent when
    citation attachment was skipped or found nothing verifiable, never fabricated."""


class MissingDocumentsForScheme(BaseModel):
    scheme_id: str
    scheme_name: str
    missing_documents: list[str]


class ChecklistResponse(BaseModel):
    bundle_id: str
    checklist_items: list[ChecklistItemOut]
    missing_by_scheme: list[MissingDocumentsForScheme] | None = None
