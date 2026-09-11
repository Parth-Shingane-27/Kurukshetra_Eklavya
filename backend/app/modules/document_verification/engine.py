"""Deterministic document-verification checks (Section 7.1 of the brief). Pure functions over
plain data — no DB, no LLM — mirroring the existing Rule/Conflict Engine pattern. Structural
checks only: this can say a document looks complete and matches a stated requirement; it can
never say a document is authentic (Section 11, rule 7) — every result carries
`authenticity_verified: False` for that reason, not as an oversight.
"""

from datetime import date, datetime

VerificationStatus = str  # "verified_structurally" | "incomplete" | "expired" | "needs_review"


def _parse_date(value: str) -> date | None:
    try:
        return datetime.fromisoformat(value).date()
    except (ValueError, TypeError):
        return None


def _mentions_document_type(document_type: str, texts: list[str]) -> bool | None:
    """True/False when we have something to compare against; None when we simply don't know
    (no required-document text was retrievable) — callers must treat None as "needs review",
    never coerce it to True or False."""
    if not texts:
        return None
    needle = document_type.strip().lower()
    return any(needle in t.lower() for t in texts if t)


def verify_document(
    document_type: str,
    required_document_texts: list[str],
    extracted_text: str | None,
    declared_fields: dict,
) -> dict:
    issues: list[str] = []
    required_match = _mentions_document_type(document_type, required_document_texts)

    if required_match is None:
        issues.append(
            f"Could not confirm '{document_type}' is a required document for this scheme from "
            "available policy data."
        )
    elif required_match is False:
        issues.append(
            f"'{document_type}' was not found among this scheme's retrieved required documents."
        )

    has_content = bool((extracted_text or "").strip()) or bool(declared_fields)
    if not has_content:
        issues.append("No extractable text and no declared fields were provided for this document.")

    expiry_raw = declared_fields.get("expiry_date")
    expired = False
    if expiry_raw:
        expiry_date = _parse_date(str(expiry_raw))
        if expiry_date is None:
            issues.append(f"Declared expiry_date '{expiry_raw}' could not be parsed.")
        elif expiry_date < date.today():
            expired = True
            issues.append(f"Document declared expiry_date {expiry_date.isoformat()} is in the past.")

    if expired:
        status: VerificationStatus = "expired"
    elif not has_content or required_match is None:
        status = "needs_review"
    elif required_match is False:
        status = "needs_review"
    else:
        status = "verified_structurally"

    human_review_required = status in ("needs_review", "expired")

    return {
        "status": status,
        "issues": issues,
        "human_review_required": human_review_required,
        "authenticity_verified": False,
    }
