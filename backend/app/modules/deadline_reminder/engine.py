"""Deterministic reminder-record construction (Section 7.2). No dates are ever invented here
— the caller supplies whatever `retrieve_deadlines` actually verified, and this module only
enforces the consent gate and shapes the stored record; it never fabricates a fallback date."""

from app.services.notification_service import send_reminder_notification


class ConsentRequiredError(ValueError):
    pass


def build_reminder_record(
    citizen_id: str,
    scheme_id: str,
    consent: bool,
    deadline_verified: bool,
    deadline_text: str | None,
) -> dict:
    if not consent:
        raise ConsentRequiredError("Explicit consent is required to create a reminder.")

    message = (
        f"Reminder for scheme {scheme_id}: {deadline_text}"
        if deadline_text
        else f"Reminder for scheme {scheme_id}: no verified deadline on file yet."
    )
    notification = send_reminder_notification(citizen_id, scheme_id, message)

    return {
        "deadline_verified": deadline_verified,
        "deadline_text": deadline_text,
        "consent_given": True,
        "notification_sent": notification["sent"],
        "notification_reason": notification["reason"],
        "status": "scheduled_internal",
    }
