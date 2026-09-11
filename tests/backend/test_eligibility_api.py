"""FR-004 — POST /api/eligibility/evaluate, end-to-end against seeded schemes (TC-007–009)."""

from bson import ObjectId

from app.modules.scheme_kb.service import seed_schemes_if_empty

BASE_CITIZEN = {
    "name": "Test Citizen",
    "date_of_birth": "1990-01-01",
    "state": "Maharashtra",
    "district": "Pune",
}


async def _create_citizen(client, **overrides):
    payload = {**BASE_CITIZEN, **overrides}
    res = await client.post("/api/citizens", json=payload)
    assert res.status_code == 201
    return res.json()["id"]


def _find(results, scheme_name):
    return next(r for r in results if r["scheme_name"] == scheme_name)


async def test_eligible_case(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(
        client, occupation="farmer", land_holding_acres=3, bpl_status=False
    )

    res = await client.post("/api/eligibility/evaluate", json={"citizen_id": citizen_id})
    assert res.status_code == 200
    result = _find(res.json()["results"], "PM-KISAN Samman Nidhi")
    assert result["status"] == "eligible"


async def test_not_eligible_case(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(
        client, occupation="farmer", land_holding_acres=12, bpl_status=False
    )

    res = await client.post("/api/eligibility/evaluate", json={"citizen_id": citizen_id})
    result = _find(res.json()["results"], "PM-KISAN Samman Nidhi")
    assert result["status"] == "not_eligible"
    assert result["reasons"][0]["field_name"] == "land_holding_acres"


async def test_indeterminate_case_missing_occupation(client, db):
    await seed_schemes_if_empty(db)
    # occupation and land_holding_acres both left unset.
    citizen_id = await _create_citizen(client, bpl_status=False)

    res = await client.post("/api/eligibility/evaluate", json={"citizen_id": citizen_id})
    result = _find(res.json()["results"], "PM-KISAN Samman Nidhi")
    assert result["status"] == "indeterminate"
    missing = {r["field_name"] for r in result["reasons"]}
    assert missing == {"occupation", "land_holding_acres"}


async def test_inactive_schemes_excluded_entirely(client, db):
    await seed_schemes_if_empty(db)
    scheme = await db.schemes.find_one({"name": "PM-KISAN Samman Nidhi"})
    await db.schemes.update_one({"_id": scheme["_id"]}, {"$set": {"is_active": False}})
    # A fully-specified profile so every remaining scheme resolves definitively
    # (not indeterminate) — isolates the BR-003 exclusion behavior being tested here.
    citizen_id = await _create_citizen(
        client,
        occupation="farmer",
        land_holding_acres=3,
        bpl_status=False,
        annual_income=200000,
        social_category="General",
        education_level="undergraduate",
        disability_status=False,
        employment_status="employed",
    )

    res = await client.post("/api/eligibility/evaluate", json={"citizen_id": citizen_id})
    assert res.status_code == 200
    names = [r["scheme_name"] for r in res.json()["results"]]
    assert "PM-KISAN Samman Nidhi" not in names
    assert len(names) == 7


async def test_citizen_not_found(client, db):
    await seed_schemes_if_empty(db)
    res = await client.post(
        "/api/eligibility/evaluate", json={"citizen_id": "64b7f0000000000000000000"}
    )
    assert res.status_code == 404


async def test_all_indeterminate_returns_409(client, db):
    await seed_schemes_if_empty(db)
    # Only the required fields are set — every seeded scheme needs at least one more.
    citizen_id = await _create_citizen(client)

    res = await client.post("/api/eligibility/evaluate", json={"citizen_id": citizen_id})
    assert res.status_code == 409


async def test_results_persisted_for_traceability(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client, occupation="farmer", land_holding_acres=3)

    res = await client.post("/api/eligibility/evaluate", json={"citizen_id": citizen_id})
    assert res.status_code == 200

    stored = await db.eligibility_results.count_documents({"citizen_id": ObjectId(citizen_id)})
    assert stored == 8  # one row per active scheme evaluated
