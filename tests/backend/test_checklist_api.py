"""FR-008/FR-009 — POST /api/checklist/generate, GET /api/checklist/:bundleId."""

from app.modules.scheme_kb.service import seed_schemes_if_empty

BASE_CITIZEN = {
    "name": "Test Citizen",
    "date_of_birth": "1975-04-20",
    "state": "Maharashtra",
    "district": "Pune",
}


async def _build_bundle(client, **citizen_overrides):
    payload = {**BASE_CITIZEN, **citizen_overrides}
    citizen_res = await client.post("/api/citizens", json=payload)
    citizen_id = citizen_res.json()["id"]
    await client.post("/api/eligibility/evaluate", json={"citizen_id": citizen_id})
    bundle_res = await client.post("/api/bundle/optimize", json={"citizen_id": citizen_id})
    return citizen_id, bundle_res.json()["bundle_id"]


async def test_generate_checklist_all_missing_when_no_documents_declared(client, db):
    await seed_schemes_if_empty(db)
    _citizen_id, bundle_id = await _build_bundle(client, bpl_status=True, annual_income=200000)

    res = await client.post("/api/checklist/generate", json={"bundle_id": bundle_id})
    assert res.status_code == 200
    body = res.json()

    # Bundle is just PMAY (state housing excluded by conflict) -> its documents are all missing.
    assert all(item["status"] == "missing" for item in body["checklist_items"])
    aadhaar = next(i for i in body["checklist_items"] if i["document_type"] == "Aadhaar Card")
    assert "Pradhan Mantri Awas Yojana (Rural)" in aadhaar["related_scheme_names"]

    missing_entry = next(m for m in body["missing_by_scheme"])
    assert missing_entry["scheme_name"] == "Pradhan Mantri Awas Yojana (Rural)"
    assert "Aadhaar Card" in missing_entry["missing_documents"]


async def test_generate_checklist_marks_declared_documents_held(client, db):
    await seed_schemes_if_empty(db)
    citizen_id, bundle_id = await _build_bundle(client, bpl_status=True, annual_income=200000)

    await client.post(
        f"/api/citizens/{citizen_id}/documents",
        json={"documents": [{"document_type": "Aadhaar Card", "held": True}]},
    )

    res = await client.post("/api/checklist/generate", json={"bundle_id": bundle_id})
    body = res.json()
    by_type = {i["document_type"]: i["status"] for i in body["checklist_items"]}
    assert by_type["Aadhaar Card"] == "held"
    assert by_type["BPL Ration Card"] == "missing"


async def test_checklist_persisted_and_retrievable(client, db):
    await seed_schemes_if_empty(db)
    _citizen_id, bundle_id = await _build_bundle(client, bpl_status=True, annual_income=200000)
    generated = await client.post("/api/checklist/generate", json={"bundle_id": bundle_id})

    res = await client.get(f"/api/checklist/{bundle_id}")
    assert res.status_code == 200
    assert res.json()["checklist_items"] == generated.json()["checklist_items"]
    assert res.json()["missing_by_scheme"] is None  # only computed fresh on generate


async def test_checklist_bundle_not_found(client, db):
    await seed_schemes_if_empty(db)
    res = await client.post("/api/checklist/generate", json={"bundle_id": "64b7f0000000000000000000"})
    assert res.status_code == 404

    res = await client.get("/api/checklist/64b7f0000000000000000000")
    assert res.status_code == 404


async def test_bundle_optimize_includes_explanation_text(client, db):
    await seed_schemes_if_empty(db)
    _citizen_id, bundle_id = await _build_bundle(client, bpl_status=True, annual_income=200000)

    res = await client.get(f"/api/bundle/{bundle_id}")
    explanation = res.json()["explanation_text"]
    assert explanation  # non-empty: template fallback fires since no GEMINI_API_KEY in test env
    assert "Pradhan Mantri Awas Yojana (Rural)" in explanation
