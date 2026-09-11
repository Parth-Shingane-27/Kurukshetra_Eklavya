"""Deterministic grievance-ticket construction (Section 7.3). `is_official_submission` is
always False here — there is no real government grievance-portal integration in this
prototype, so this can only ever create an internal platform ticket (Section 11, rule 8:
"Never claim a grievance was officially filed without a real integration")."""

import uuid


def build_grievance_ticket(
    category: str,
    description: str,
    scheme_id: str | None,
    department: str | None,
) -> dict:
    return {
        "ticket_id": f"ASBO-GRV-{uuid.uuid4().hex[:10].upper()}",
        "scheme_id": scheme_id,
        "category": category,
        "description": description,
        "department": department,
        "is_official_submission": False,
        "status": "open",
    }
