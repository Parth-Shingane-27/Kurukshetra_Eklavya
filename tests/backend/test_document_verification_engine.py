"""Document Verification Agent — deterministic engine tests (Section 7.1). Pure functions,
no DB, no LLM. Every result must carry authenticity_verified=False (Section 11, rule 7)."""

from datetime import date, timedelta

from app.modules.document_verification.engine import verify_document


def test_verified_structurally_when_required_and_content_present():
    outcome = verify_document(
        "Aadhaar Card",
        required_document_texts=["Aadhaar Card (mandatory)", "Bank Passbook (mandatory)"],
        extracted_text="This is the Aadhaar Card of the applicant.",
        declared_fields={},
    )
    assert outcome["status"] == "verified_structurally"
    assert outcome["human_review_required"] is False
    assert outcome["authenticity_verified"] is False
    assert outcome["issues"] == []


def test_needs_review_when_document_type_not_in_required_list():
    outcome = verify_document(
        "Passport",
        required_document_texts=["Aadhaar Card (mandatory)"],
        extracted_text="Some text",
        declared_fields={},
    )
    assert outcome["status"] == "needs_review"
    assert outcome["human_review_required"] is True
    assert any("not found among" in i for i in outcome["issues"])


def test_needs_review_when_no_required_documents_retrievable():
    outcome = verify_document(
        "Aadhaar Card", required_document_texts=[], extracted_text="Some text", declared_fields={}
    )
    assert outcome["status"] == "needs_review"
    assert outcome["human_review_required"] is True
    assert any("Could not confirm" in i for i in outcome["issues"])


def test_incomplete_when_no_content_at_all():
    outcome = verify_document(
        "Aadhaar Card",
        required_document_texts=["Aadhaar Card (mandatory)"],
        extracted_text=None,
        declared_fields={},
    )
    assert outcome["status"] == "needs_review"
    assert any("No extractable text" in i for i in outcome["issues"])


def test_expired_when_declared_expiry_in_the_past():
    past = (date.today() - timedelta(days=1)).isoformat()
    outcome = verify_document(
        "Income Certificate",
        required_document_texts=["Income Certificate (mandatory)"],
        extracted_text="Income certificate text",
        declared_fields={"expiry_date": past},
    )
    assert outcome["status"] == "expired"
    assert outcome["human_review_required"] is True


def test_not_expired_when_declared_expiry_in_the_future():
    future = (date.today() + timedelta(days=30)).isoformat()
    outcome = verify_document(
        "Income Certificate",
        required_document_texts=["Income Certificate (mandatory)"],
        extracted_text="Income certificate text",
        declared_fields={"expiry_date": future},
    )
    assert outcome["status"] == "verified_structurally"


def test_authenticity_never_claimed_true():
    outcome = verify_document(
        "Aadhaar Card", required_document_texts=["Aadhaar Card"], extracted_text="text", declared_fields={}
    )
    assert outcome["authenticity_verified"] is False
