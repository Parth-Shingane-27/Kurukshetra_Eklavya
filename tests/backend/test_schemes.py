"""FR-003 — List/get schemes, and the seed loader (TC-006)."""

from app.modules.scheme_kb.service import seed_schemes_if_empty


async def test_list_active_schemes_only(client, db):
    await seed_schemes_if_empty(db)
    scheme = await db.schemes.find_one({"name": "PM-KISAN Samman Nidhi"})
    await db.schemes.update_one({"_id": scheme["_id"]}, {"$set": {"is_active": False}})

    res = await client.get("/api/schemes")
    assert res.status_code == 200
    names = [s["name"] for s in res.json()]
    assert "PM-KISAN Samman Nidhi" not in names
    assert len(names) == 7


async def test_list_schemes_filter_by_category(client, db):
    await seed_schemes_if_empty(db)
    res = await client.get("/api/schemes", params={"category": "Housing & Shelter"})
    assert res.status_code == 200
    names = {s["name"] for s in res.json()}
    assert names == {"Pradhan Mantri Awas Yojana (Rural)", "State Rural Housing Assistance Scheme"}


async def test_get_scheme_by_id(client, db):
    await seed_schemes_if_empty(db)
    scheme = await db.schemes.find_one({"name": "Disability Pension Scheme"})

    res = await client.get(f"/api/schemes/{scheme['_id']}")
    assert res.status_code == 200
    assert res.json()["name"] == "Disability Pension Scheme"
    assert res.json()["document_requirements"][0]["document_type"] == "Aadhaar Card"


async def test_get_scheme_not_found(client):
    res = await client.get("/api/schemes/64b7f0000000000000000000")
    assert res.status_code == 404


async def test_seed_is_idempotent(db):
    await seed_schemes_if_empty(db)
    await seed_schemes_if_empty(db)
    assert await db.schemes.count_documents({}) == 8


async def test_seed_creates_conflict_rules(db):
    await seed_schemes_if_empty(db)
    count = await db.conflict_rules.count_documents({})
    assert count == 1
    rule = await db.conflict_rules.find_one({})
    assert rule["conflict_type"] == "mutually_exclusive"
