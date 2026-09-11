"""FR-011 — Admin conflict declaration (BR-004), the piece the Phase 8 audit found missing."""

from app.core.config import get_settings
from app.modules.scheme_kb.service import seed_schemes_if_empty

ADMIN_HEADERS = {"X-Admin-Token": get_settings().admin_credential}


async def _seed_two_schemes(db):
    await seed_schemes_if_empty(db)
    a = await db.schemes.find_one({"name": "Skill Development Training Stipend"})
    b = await db.schemes.find_one({"name": "State Unemployment Allowance Scheme"})
    return str(a["_id"]), str(b["_id"])


async def test_list_conflict_rules_public_and_includes_seed_pair(client, db):
    await seed_schemes_if_empty(db)
    res = await client.get("/api/conflict-rules")
    assert res.status_code == 200
    rules = res.json()
    assert len(rules) == 1
    assert {rules[0]["scheme_a_name"], rules[0]["scheme_b_name"]} == {
        "Skill Development Training Stipend",
        "State Unemployment Allowance Scheme",
    }


async def test_create_conflict_rule_requires_admin_token(client, db):
    a_id, b_id = await _seed_two_schemes(db)
    res = await client.post(
        "/api/conflict-rules", json={"scheme_a_id": a_id, "scheme_b_id": b_id, "conflict_type": "mutually_exclusive"}
    )
    assert res.status_code == 401


async def test_create_conflict_rule_valid(client, db):
    await seed_schemes_if_empty(db)
    a = await db.schemes.find_one({"name": "PM-KISAN Samman Nidhi"})
    b = await db.schemes.find_one({"name": "Disability Pension Scheme"})
    res = await client.post(
        "/api/conflict-rules",
        json={
            "scheme_a_id": str(a["_id"]),
            "scheme_b_id": str(b["_id"]),
            "conflict_type": "mutually_exclusive",
            "reason": "test-declared conflict",
        },
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 201
    body = res.json()
    assert body["scheme_a_name"] == "PM-KISAN Samman Nidhi"
    assert body["scheme_b_name"] == "Disability Pension Scheme"

    listed = await client.get("/api/conflict-rules")
    assert len(listed.json()) == 2  # the seed pair + this new one


async def test_create_conflict_rule_rejects_same_scheme_twice(client, db):
    await seed_schemes_if_empty(db)
    a = await db.schemes.find_one({"name": "PM-KISAN Samman Nidhi"})
    res = await client.post(
        "/api/conflict-rules",
        json={"scheme_a_id": str(a["_id"]), "scheme_b_id": str(a["_id"]), "conflict_type": "mutually_exclusive"},
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 422


async def test_create_conflict_rule_rejects_unknown_scheme(client, db):
    await seed_schemes_if_empty(db)
    a = await db.schemes.find_one({"name": "PM-KISAN Samman Nidhi"})
    res = await client.post(
        "/api/conflict-rules",
        json={
            "scheme_a_id": str(a["_id"]),
            "scheme_b_id": "64b7f0000000000000000000",
            "conflict_type": "mutually_exclusive",
        },
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 404


async def test_admin_declared_conflict_affects_subsequent_optimization(client, db):
    """The new conflict must actually be picked up by the Conflict Detection Engine and
    Bundle Optimizer on the very next run — not just stored inertly."""
    await seed_schemes_if_empty(db)
    pm_kisan = await db.schemes.find_one({"name": "PM-KISAN Samman Nidhi"})
    old_age = await db.schemes.find_one({"name": "National Old Age Pension Scheme (IGNOAPS)"})

    await client.post(
        "/api/conflict-rules",
        json={
            "scheme_a_id": str(pm_kisan["_id"]),
            "scheme_b_id": str(old_age["_id"]),
            "conflict_type": "mutually_exclusive",
            "reason": "test",
        },
        headers=ADMIN_HEADERS,
    )

    citizen_res = await client.post(
        "/api/citizens",
        json={
            "name": "Conflict Test",
            "date_of_birth": "1960-01-01",
            "state": "Bihar",
            "district": "Patna",
            "occupation": "farmer",
            "land_holding_acres": 2,
            "bpl_status": True,
        },
    )
    citizen_id = citizen_res.json()["id"]
    await client.post("/api/eligibility/evaluate", json={"citizen_id": citizen_id})

    conflicts = await client.post("/api/conflicts/detect", json={"citizen_id": citizen_id})
    assert any(c["conflict_type"] == "mutually_exclusive" for c in conflicts.json()["conflicts"])

    bundle = await client.post("/api/bundle/optimize", json={"citizen_id": citizen_id})
    excluded_names = {e["scheme_name"] for e in bundle.json()["excluded"]}
    assert len(excluded_names & {"PM-KISAN Samman Nidhi", "National Old Age Pension Scheme (IGNOAPS)"}) == 1
