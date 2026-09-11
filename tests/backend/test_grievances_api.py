"""Feedback/Grievance Agent — API tests. Uses a curated seed scheme (issuing_authority in
Mongo) to verify department resolution, and an unknown scheme to verify the honest "no
department found" path (Section 7.3/11)."""

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


async def test_create_grievance_resolves_department_from_curated_scheme(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)

    res = await client.post(
        "/api/grievances",
        json={
            "citizen_id": citizen_id, "scheme_id": scheme_id,
            "category": "delay", "description": "My application has been pending for weeks.",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["is_official_submission"] is False
    assert body["department"] == "Issuing authority: Ministry of Agriculture and Farmers Welfare"
    assert body["status"] == "open"


async def test_create_grievance_without_scheme_has_no_department(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)

    res = await client.post(
        "/api/grievances",
        json={"citizen_id": citizen_id, "category": "general", "description": "Platform feedback."},
    )
    assert res.status_code == 201
    assert res.json()["department"] is None


async def test_create_grievance_rejects_blank_description(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    res = await client.post(
        "/api/grievances", json={"citizen_id": citizen_id, "category": "general", "description": "   "}
    )
    assert res.status_code == 422


async def test_create_grievance_citizen_not_found(client, db):
    res = await client.post(
        "/api/grievances",
        json={"citizen_id": "64b7f0000000000000000000", "category": "general", "description": "text"},
    )
    assert res.status_code == 404


async def test_get_and_list_grievances(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    created = await client.post(
        "/api/grievances",
        json={"citizen_id": citizen_id, "category": "general", "description": "text"},
    )
    grievance_id = created.json()["id"]

    got = await client.get(f"/api/grievances/{grievance_id}")
    assert got.status_code == 200
    assert got.json()["ticket_id"] == created.json()["ticket_id"]

    listed = await client.get(f"/api/grievances/citizen/{citizen_id}")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
