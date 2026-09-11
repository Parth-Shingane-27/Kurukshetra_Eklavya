"""Feedback/Grievance Agent — deterministic engine tests (Section 7.3). A ticket must never
claim to be an official government submission (Section 11, rule 8)."""

from app.modules.feedback_grievance.engine import build_grievance_ticket


def test_ticket_is_never_official_submission():
    ticket = build_grievance_ticket("delay", "My application is stuck", "scheme-1", "Dept of Welfare")
    assert ticket["is_official_submission"] is False
    assert ticket["status"] == "open"
    assert ticket["ticket_id"].startswith("ASBO-GRV-")


def test_ticket_department_none_when_unavailable():
    ticket = build_grievance_ticket("delay", "My application is stuck", None, None)
    assert ticket["department"] is None
    assert ticket["scheme_id"] is None


def test_ticket_ids_are_unique():
    a = build_grievance_ticket("delay", "desc", None, None)
    b = build_grievance_ticket("delay", "desc", None, None)
    assert a["ticket_id"] != b["ticket_id"]
