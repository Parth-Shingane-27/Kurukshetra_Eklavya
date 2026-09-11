"""Fraud Detection Agent — deterministic engine tests (Section 7.5). Never sets a "confirmed"
verdict; human_review_required is always True once any indicator is found (Section 11, rule 10)."""

from app.modules.fraud_detection.engine import screen_for_fraud_risk


def _verification(**overrides):
    base = {
        "id": "v1", "scheme_id": "s1", "document_type": "Aadhaar Card",
        "status": "verified_structurally", "issues": [], "declared_fields": {},
    }
    base.update(overrides)
    return base


def test_low_risk_when_no_issues():
    result = screen_for_fraud_risk([_verification()])
    assert result["risk_level"] == "low"
    assert result["human_review_required"] is False
    assert result["indicators"] == []
    assert "fraud_confirmed" not in result


def test_document_type_mismatch_indicator():
    v = _verification(status="needs_review", issues=["'X' was not found among this scheme's retrieved required documents."])
    result = screen_for_fraud_risk([v])
    assert result["risk_level"] == "medium"
    assert result["human_review_required"] is True
    assert result["indicators"][0]["type"] == "document_type_mismatch"


def test_expired_document_indicator():
    v = _verification(status="expired", issues=["Document declared expiry_date 2020-01-01 is in the past."])
    result = screen_for_fraud_risk([v])
    assert any(i["type"] == "date_inconsistency" for i in result["indicators"])


def test_duplicate_submission_indicator():
    v1 = _verification(id="v1")
    v2 = _verification(id="v2")
    result = screen_for_fraud_risk([v1, v2])
    assert any(i["type"] == "duplicate_submission" for i in result["indicators"])


def test_cross_document_conflict_indicator():
    v1 = _verification(id="v1", document_type="Aadhaar Card", declared_fields={"name": "Ramesh"})
    v2 = _verification(id="v2", document_type="Bank Passbook", declared_fields={"name": "Suresh"})
    result = screen_for_fraud_risk([v1, v2])
    assert any(i["type"] == "cross_document_conflict" for i in result["indicators"])


def test_multiple_indicators_escalate_to_high_risk():
    v1 = _verification(id="v1", status="expired", issues=["Document declared expiry_date 2020-01-01 is in the past."])
    v2 = _verification(id="v2", status="needs_review", issues=["'X' was not found among this scheme's retrieved required documents."])
    result = screen_for_fraud_risk([v1, v2])
    assert result["risk_level"] == "high"
    assert result["human_review_required"] is True
