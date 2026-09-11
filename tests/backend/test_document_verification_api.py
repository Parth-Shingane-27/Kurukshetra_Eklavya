"""Document Verification Agent — API tests. Uses the curated seed schemes (Mongo ObjectId
scheme_id), so PolicyKnowledgeService resolves required documents via the structured
`schemes` collection and never touches the vector store/embeddings — no GEMINI_API_KEY or
mocked retriever needed for these tests, matching PolicyKnowledgeService's lazy-retriever
design (app/rag/policy_service.py).
"""

import base64

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


async def test_verify_document_verified_structurally(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)

    res = await client.post(
        "/api/documents/verify",
        json={
            "citizen_id": citizen_id,
            "scheme_id": scheme_id,
            "document_type": "Aadhaar Card",
            "document_text": "This is the applicant's Aadhaar Card, number XXXX-XXXX-1234.",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "verified_structurally"
    assert body["authenticity_verified"] is False
    assert body["human_review_required"] is False


async def test_verify_document_needs_review_when_not_a_required_document(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)

    res = await client.post(
        "/api/documents/verify",
        json={
            "citizen_id": citizen_id,
            "scheme_id": scheme_id,
            "document_type": "Passport",
            "document_text": "Passport document text",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "needs_review"
    assert body["human_review_required"] is True


async def test_verify_document_citizen_not_found(client, db):
    await seed_schemes_if_empty(db)
    scheme_id = await _pm_kisan_scheme_id(db)
    res = await client.post(
        "/api/documents/verify",
        json={
            "citizen_id": "64b7f0000000000000000000",
            "scheme_id": scheme_id,
            "document_type": "Aadhaar Card",
            "document_text": "text",
        },
    )
    assert res.status_code == 404


async def test_verify_document_requires_some_content(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)
    res = await client.post(
        "/api/documents/verify",
        json={"citizen_id": citizen_id, "scheme_id": scheme_id, "document_type": "Aadhaar Card"},
    )
    assert res.status_code == 422


async def test_verify_document_pdf_base64_extraction(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)
    invalid_pdf_b64 = base64.b64encode(b"not a real pdf").decode()

    res = await client.post(
        "/api/documents/verify",
        json={
            "citizen_id": citizen_id, "scheme_id": scheme_id,
            "document_type": "Aadhaar Card", "pdf_base64": invalid_pdf_b64,
        },
    )
    assert res.status_code == 422  # unparseable PDF is a client error, not a server crash


async def test_get_and_list_verifications(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)
    created = await client.post(
        "/api/documents/verify",
        json={
            "citizen_id": citizen_id, "scheme_id": scheme_id,
            "document_type": "Aadhaar Card", "document_text": "Aadhaar Card text",
        },
    )
    verification_id = created.json()["id"]

    got = await client.get(f"/api/documents/verify/{verification_id}")
    assert got.status_code == 200
    assert got.json()["id"] == verification_id

    listed = await client.get(f"/api/documents/verify/citizen/{citizen_id}")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
