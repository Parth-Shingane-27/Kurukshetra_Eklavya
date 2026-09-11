from typing import Literal

from pydantic import BaseModel


class GenerateChecklistRequest(BaseModel):
    bundle_id: str


class ChecklistItemOut(BaseModel):
    document_type: str
    related_scheme_ids: list[str]
    related_scheme_names: list[str]
    status: Literal["missing", "held"]


class MissingDocumentsForScheme(BaseModel):
    scheme_id: str
    scheme_name: str
    missing_documents: list[str]


class ChecklistResponse(BaseModel):
    bundle_id: str
    checklist_items: list[ChecklistItemOut]
    missing_by_scheme: list[MissingDocumentsForScheme] | None = None
