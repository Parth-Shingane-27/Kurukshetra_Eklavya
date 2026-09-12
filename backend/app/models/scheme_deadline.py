from datetime import datetime

from pydantic import BaseModel


class SchemeDeadlineOut(BaseModel):
    """Public, citizen-independent deadline info for a scheme card — distinct from
    `app.models.deadline_reminder.ReminderOut`, which is a citizen-specific, consent-gated
    record. This is just read-only informational text, the same underlying
    `retrieve_deadlines()` extraction, shown on the scheme catalog for every visitor."""

    scheme_id: str
    available: bool
    deadline_text: str | None = None
    reason: str | None = None
    """Why no deadline is available, when `available` is False — shown honestly instead of a
    blank space, never a fabricated date."""
    last_checked_at: datetime
    cached: bool
