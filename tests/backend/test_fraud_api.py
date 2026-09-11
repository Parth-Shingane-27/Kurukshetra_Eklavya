"""Fraud Detection Agent — API tests. Builds real document_verifications via the Document
Verification Agent's own endpoint first (no duplicated fixture logic), then screens them."""

from app.modules.scheme_kb.service import seed_schemes_if_empty

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

    res = await client.post("/api/fraud/screen", json={"citizen_id": citizen_id})
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

    res = await client.post("/api/fraud/screen", json={"citizen_id": citizen_id})
    body = res.json()
    assert body["risk_level"] != "low"
    assert body["human_review_required"] is True
    assert any(i["type"] == "document_type_mismatch" for i in body["indicators"])
    assert "summary" in body and body["summary"]


async def test_screen_citizen_not_found(client, db):
    res = await client.post("/api/fraud/screen", json={"citizen_id": "64b7f0000000000000000000"})
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

    res = await client.post("/api/fraud/screen", json={"citizen_id": citizen_id, "scheme_id": "some-other-scheme"})
    assert res.status_code == 201
    assert res.json()["indicators"] == []  # nothing screened for an unrelated scheme_id


async def test_get_and_list_fraud_flags(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    created = await client.post("/api/fraud/screen", json={"citizen_id": citizen_id})
    flag_id = created.json()["id"]

    got = await client.get(f"/api/fraud/{flag_id}")
    assert got.status_code == 200

    listed = await client.get(f"/api/fraud/citizen/{citizen_id}")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
