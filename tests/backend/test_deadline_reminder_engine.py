"""Deadline/Reminder Agent — deterministic engine tests (Section 7.2). No date is ever
invented; consent is a hard gate; notification_sent must always be False in this prototype
(Section 11, rule 9 — no real notification provider is configured)."""

import pytest

from app.modules.deadline_reminder.engine import ConsentRequiredError, build_reminder_record


def test_consent_required_raises_when_false():
    with pytest.raises(ConsentRequiredError):
        build_reminder_record("c1", "s1", consent=False, deadline_verified=True, deadline_text="within 30 days")


def test_reminder_never_claims_notification_sent():
    record = build_reminder_record("c1", "s1", consent=True, deadline_verified=True, deadline_text="within 30 days")
    assert record["notification_sent"] is False
    assert "no notification provider configured" in record["notification_reason"]
    assert record["status"] == "scheduled_internal"


def test_reminder_honest_when_no_deadline_verified():
    record = build_reminder_record("c1", "s1", consent=True, deadline_verified=False, deadline_text=None)
    assert record["deadline_verified"] is False
    assert record["deadline_text"] is None
    # Still creatable (citizen may want a generic internal reminder) but never with an
    # invented date.
    assert record["status"] == "scheduled_internal"
