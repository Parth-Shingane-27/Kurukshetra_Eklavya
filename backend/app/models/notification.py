"""In-app Notification Center. Deliberately NOT an email/SMS delivery system — no real
provider is configured anywhere in this app (see `app/services/notification_service.py`'s
always-`sent: False` stub); this is an in-app feed only, built from real events that already
happen in the system (a grievance created/resolved, a reminder the citizen explicitly
requested), never a fabricated or scheduled push."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

NotificationType = Literal["grievance_created", "grievance_resolved", "deadline_reminder"]


class NotificationOut(BaseModel):
    id: str
    citizen_id: str
    type: NotificationType
    message: str
    related_id: str | None = None
    read: bool
    created_at: datetime


class MarkReadRequest(BaseModel):
    notification_id: str
