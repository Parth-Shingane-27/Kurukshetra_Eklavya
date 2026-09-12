"""Citizen-facing live web scheme search — distinct from `scheme_discovery` (which queues
proposals for admin approval before they ever become a real scheme). Here, results are shown
directly to the citizen who searched for them, always labeled unverified, and never written to
the curated `schemes` collection. Reuses `DiscoveredSchemeDraft` from `scheme_discovery` for the
same Gemini structured-output shape rather than duplicating it.
"""

from datetime import datetime

from pydantic import BaseModel

from app.models.scheme_discovery import DiscoveredSchemeDraft


class WebSchemeSearchResponse(BaseModel):
    citizen_id: str
    query: str
    generated_at: datetime
    suggestions: list[DiscoveredSchemeDraft]
    stale: bool = False
    """True when this is a cached result served because a fresh search was skipped (no
    TAVILY_API_KEY/GEMINI_API_KEY) or failed, not because it's still within the cache TTL."""
