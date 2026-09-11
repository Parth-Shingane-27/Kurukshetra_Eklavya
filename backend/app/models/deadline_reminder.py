from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ReminderStatus = Literal["scheduled_internal"]


class CreateReminderRequest(BaseModel):
    citizen_id: str
    scheme_id: str
    consent: bool


class ReminderOut(BaseModel):
    id: str
    citizen_id: str
    scheme_id: str
    deadline_verified: bool
    deadline_text: str | None
    consent_given: bool
    notification_sent: bool
    """Always False in this prototype (Section 11, rule 9) — no real notification provider is
    configured; see app/services/notification_service.py."""
    notification_reason: str
    status: ReminderStatus
    created_at: datetime
