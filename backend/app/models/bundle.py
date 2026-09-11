from datetime import datetime

from pydantic import BaseModel


class ConflictDetectRequest(BaseModel):
    citizen_id: str


class ConflictEntry(BaseModel):
    scheme_a_id: str
    scheme_a_name: str
    scheme_b_id: str
    scheme_b_name: str
    conflict_type: str
    reason: str


class ConflictDetectResponse(BaseModel):
    citizen_id: str
    conflicts: list[ConflictEntry]


class BundleOptimizeRequest(BaseModel):
    citizen_id: str


class ExcludedScheme(BaseModel):
    scheme_id: str
    scheme_name: str
    reason: str


class BundleOut(BaseModel):
    bundle_id: str
    citizen_id: str
    scheme_ids: list[str]
    total_benefit_value: float
    excluded: list[ExcludedScheme]
    explanation_text: str | None = None
    generated_at: datetime
