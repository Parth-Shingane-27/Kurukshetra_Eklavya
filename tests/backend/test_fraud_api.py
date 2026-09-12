"""Fraud Detection Agent — API tests. Builds real document_verifications via the Document
Verification Agent's own endpoint first (no duplicated fixture logic), then screens them.

Every /api/fraud/* route is admin-only (an internal trust-and-safety control, not
citizen-facing) — all calls below carry the admin credential header."""

from app.core.config import get_settings
from app.modules.scheme_kb.service import seed_schemes_if_empty

ADMIN_HEADERS = {"X-Admin-Token": get_settings().admin_credential}

BASE_CITIZEN = {
    "name": "Test Citizen",
    "date_of_birth": "1990-01-01",
    "state": "Bihar",
    "district": "Patna",
}


async def _create_citizen(client):
    res = await client.post("/api/citizens", json=BASE_CITIZEN)
    return res.json()["id"]


async def _pm_kisan_scheme_id(db):
    scheme = await db.schemes.find_one({"name": "PM-KISAN Samman Nidhi"})
    return str(scheme["_id"])


async def test_screen_low_risk_when_documents_clean(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)
    await client.post(
        "/api/documents/verify",
        json={
            "citizen_id": citizen_id, "scheme_id": scheme_id,
            "document_type": "Aadhaar Card", "document_text": "Aadhaar Card text",
        },
    )

    res = await client.post("/api/fraud/screen", json={"citizen_id": citizen_id}, headers=ADMIN_HEADERS)
    assert res.status_code == 201
    body = res.json()
    assert body["risk_level"] == "low"
    assert body["human_review_required"] is False
    assert body["indicators"] == []


async def test_screen_flags_mismatched_document_and_requires_review(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)
    await client.post(
        "/api/documents/verify",
        json={
            "citizen_id": citizen_id, "scheme_id": scheme_id,
            "document_type": "Passport", "document_text": "Passport text",
        },
    )

    res = await client.post("/api/fraud/screen", json={"citizen_id": citizen_id}, headers=ADMIN_HEADERS)
    body = res.json()
    assert body["risk_level"] != "low"
    assert body["human_review_required"] is True
    assert any(i["type"] == "document_type_mismatch" for i in body["indicators"])
    assert "summary" in body and body["summary"]


async def test_screen_citizen_not_found(client, db):
    res = await client.post("/api/fraud/screen", json={"citizen_id": "64b7f0000000000000000000"}, headers=ADMIN_HEADERS)
    assert res.status_code == 404


async def test_screen_scoped_to_scheme_id(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)
    await client.post(
        "/api/documents/verify",
        json={
            "citizen_id": citizen_id, "scheme_id": scheme_id,
            "document_type": "Aadhaar Card", "document_text": "text",
        },
    )

    res = await client.post("/api/fraud/screen", json={"citizen_id": citizen_id, "scheme_id": "some-other-scheme"}, headers=ADMIN_HEADERS)
    assert res.status_code == 201
    assert res.json()["indicators"] == []  # nothing screened for an unrelated scheme_id


async def test_get_and_list_fraud_flags(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    created = await client.post("/api/fraud/screen", json={"citizen_id": citizen_id}, headers=ADMIN_HEADERS)
    flag_id = created.json()["id"]

    got = await client.get(f"/api/fraud/{flag_id}", headers=ADMIN_HEADERS)
    assert got.status_code == 200

    listed = await client.get(f"/api/fraud/citizen/{citizen_id}", headers=ADMIN_HEADERS)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


async def test_admin_can_list_all_fraud_flags_with_filters(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)
    await client.post(
        "/api/documents/verify",
        json={"citizen_id": citizen_id, "scheme_id": scheme_id, "document_type": "Passport", "document_text": "Passport text"},
    )
    await client.post("/api/fraud/screen", json={"citizen_id": citizen_id}, headers=ADMIN_HEADERS)

    all_res = await client.get("/api/fraud", headers=ADMIN_HEADERS)
    assert all_res.status_code == 200
    assert len(all_res.json()) == 1

    filtered_res = await client.get("/api/fraud", params={"reviewed": False}, headers=ADMIN_HEADERS)
    assert len(filtered_res.json()) == 1
    none_res = await client.get("/api/fraud", params={"reviewed": True}, headers=ADMIN_HEADERS)
    assert none_res.json() == []


async def test_non_admin_cannot_list_all_fraud_flags(client, db):
    res = await client.get("/api/fraud")
    assert res.status_code in (401, 403)


async def test_admin_can_review_fraud_flag(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)
    await client.post(
        "/api/documents/verify",
        json={"citizen_id": citizen_id, "scheme_id": scheme_id, "document_type": "Passport", "document_text": "Passport text"},
    )
    created = await client.post("/api/fraud/screen", json={"citizen_id": citizen_id}, headers=ADMIN_HEADERS)
    flag_id = created.json()["id"]

    res = await client.post(
        f"/api/fraud/{flag_id}/review", json={"reviewer_notes": "Checked manually — false positive."}, headers=ADMIN_HEADERS
    )
    assert res.status_code == 200
    body = res.json()
    assert body["reviewed"] is True
    assert body["reviewer_notes"] == "Checked manually — false positive."
    assert body["reviewed_at"] is not None


async def test_cannot_review_already_reviewed_flag(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)
    await client.post(
        "/api/documents/verify",
        json={"citizen_id": citizen_id, "scheme_id": scheme_id, "document_type": "Passport", "document_text": "Passport text"},
    )
    created = await client.post("/api/fraud/screen", json={"citizen_id": citizen_id}, headers=ADMIN_HEADERS)
    flag_id = created.json()["id"]
    await client.post(f"/api/fraud/{flag_id}/review", json={"reviewer_notes": "x"}, headers=ADMIN_HEADERS)

    res = await client.post(f"/api/fraud/{flag_id}/review", json={"reviewer_notes": "y"}, headers=ADMIN_HEADERS)
    assert res.status_code == 400
