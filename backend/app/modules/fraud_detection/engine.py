"""Deterministic fraud-risk screening (Section 7.5). Pure functions over already-computed
Document Verification records — no LLM, no new "is this person a fraudster" judgment call.
Only ever produces *risk indicators* + a `risk_level`; never a `fraud_confirmed` field, and
`human_review_required` is always True once risk is non-trivial (Section 11, rule 10: "Never
claim fraud based solely on an LLM output"; Section 7.5: "Do not label users as fraudsters").
"""

from collections import Counter

RiskLevel = str  # "low" | "medium" | "high"


def screen_for_fraud_risk(verifications: list[dict]) -> dict:
    indicators: list[dict] = []

    mismatched = [
        v for v in verifications
        if v["status"] == "needs_review" and any("not found among" in i for i in v["issues"])
    ]
    if mismatched:
        indicators.append(
            {
                "type": "document_type_mismatch",
                "detail": f"{len(mismatched)} document(s) did not match this scheme's retrieved requirements.",
                "verification_ids": [v["id"] for v in mismatched],
            }
        )

    incomplete = [v for v in verifications if any("No extractable text" in i for i in v["issues"])]
    if incomplete:
        indicators.append(
            {
                "type": "missing_required_fields",
                "detail": f"{len(incomplete)} document(s) had no extractable text or declared fields.",
                "verification_ids": [v["id"] for v in incomplete],
            }
        )

    expired = [v for v in verifications if v["status"] == "expired"]
    if expired:
        indicators.append(
            {
                "type": "date_inconsistency",
                "detail": f"{len(expired)} document(s) are expired per their declared expiry date.",
                "verification_ids": [v["id"] for v in expired],
            }
        )

    duplicate_counts = Counter((v["scheme_id"], v["document_type"]) for v in verifications)
    duplicate_keys = [k for k, count in duplicate_counts.items() if count > 1]
    if duplicate_keys:
        indicators.append(
            {
                "type": "duplicate_submission",
                "detail": f"{len(duplicate_keys)} (scheme, document type) pair(s) were submitted more than once.",
                "verification_ids": [
                    v["id"] for v in verifications if (v["scheme_id"], v["document_type"]) in duplicate_keys
                ],
            }
        )

    field_values: dict[str, set[str]] = {}
    field_sources: dict[str, list[str]] = {}
    for v in verifications:
        for key, value in (v.get("declared_fields") or {}).items():
            field_values.setdefault(key, set()).add(str(value))
            field_sources.setdefault(key, []).append(v["id"])
    conflicting_fields = [k for k, values in field_values.items() if len(values) > 1]
    if conflicting_fields:
        indicators.append(
            {
                "type": "cross_document_conflict",
                "detail": f"Declared field(s) {', '.join(conflicting_fields)} differ across submitted documents.",
                "verification_ids": sorted({vid for k in conflicting_fields for vid in field_sources[k]}),
            }
        )

    if not indicators:
        risk_level: RiskLevel = "low"
    elif len(indicators) == 1:
        risk_level = "medium"
    else:
        risk_level = "high"

    return {
        "indicators": indicators,
        "risk_level": risk_level,
        "human_review_required": risk_level != "low",
    }
