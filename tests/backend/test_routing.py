"""Intent routing — pure function, deterministic (Section 8 of the brief)."""

from app.graph.routing import detect_intent


def test_check_eligibility_intent():
    assert detect_intent("Am I eligible for any farmer schemes?") == "CHECK_ELIGIBILITY"


def test_discover_scheme_intent():
    assert detect_intent("What schemes for widows are available?") == "DISCOVER_SCHEME"


def test_verify_document_intent():
    assert detect_intent("Can you verify document I uploaded?") == "VERIFY_DOCUMENT"


def test_check_deadline_intent():
    assert detect_intent("What is the last date to apply?") == "CHECK_DEADLINE"


def test_set_reminder_intent():
    assert detect_intent("Please remind me about this scheme") == "SET_REMINDER"


def test_register_grievance_intent():
    assert detect_intent("I want to file a complaint about my application") == "REGISTER_GRIEVANCE"


def test_check_grievance_status_intent():
    assert detect_intent("What is the status of my complaint ticket?") == "CHECK_GRIEVANCE_STATUS"


def test_report_suspicious_activity_intent():
    assert detect_intent("This looks like a fake document, I want to report fraud") == "REPORT_SUSPICIOUS_ACTIVITY"


def test_change_language_intent():
    assert detect_intent("Please switch language to Hindi") == "CHANGE_LANGUAGE"


def test_compare_schemes_intent():
    assert detect_intent("Compare PM-KISAN and the state housing scheme") == "COMPARE_SCHEMES"


def test_ambiguous_falls_back_to_general_query():
    assert detect_intent("Tell me something interesting") == "GENERAL_QUERY"


def test_empty_query_falls_back_to_general_query():
    assert detect_intent("") == "GENERAL_QUERY"
