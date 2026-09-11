"""Notification stub (Section 11, rule 9 of the brief: "Never claim a reminder was sent
unless the notification service confirms it"). No SMS/email/push provider is configured in
this prototype, so this always reports `sent: False` — a real provider integration would
replace only this module, without any caller needing to change (Deadline/Reminder Agent
records `status: "scheduled_internal"`, never "sent", based on this result).
"""


def send_reminder_notification(citizen_id: str, scheme_id: str, message: str) -> dict:
    return {
        "sent": False,
        "reason": "no notification provider configured (prototype stub)",
    }
