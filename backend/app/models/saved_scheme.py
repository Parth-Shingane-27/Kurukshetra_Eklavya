"""Saved/watchlist schemes — a citizen bookmarking a scheme for later (whether or not they're
currently eligible for it), independent of any eligibility computation."""

from datetime import datetime

from pydantic import BaseModel


class SaveSchemeRequest(BaseModel):
    scheme_id: str


class SavedSchemeOut(BaseModel):
    id: str
    citizen_id: str
    scheme_id: str
    scheme_name: str
    scheme_category: str
    saved_at: datetime
