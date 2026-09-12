"""Admin analytics — real, deterministic counts/aggregations over this app's own collections.
No LLM involved, no invented metrics: every field here is a plain count or a top-N aggregation
that answers an actual operational question (how many citizens/schemes are active, how much
support-ticket/fraud-review backlog exists, which schemes citizens actually care about)."""

from pydantic import BaseModel


class CategoryCount(BaseModel):
    category: str
    count: int


class SchemeSaveCount(BaseModel):
    scheme_id: str
    scheme_name: str
    save_count: int


class AnalyticsOut(BaseModel):
    total_citizens: int
    total_active_schemes: int
    total_eligibility_evaluations: int
    total_bundles_generated: int
    open_grievances: int
    resolved_grievances: int
    fraud_flags_pending_review: int
    fraud_flags_reviewed: int
    rag_candidates_pending: int
    schemes_by_category: list[CategoryCount]
    most_saved_schemes: list[SchemeSaveCount]
