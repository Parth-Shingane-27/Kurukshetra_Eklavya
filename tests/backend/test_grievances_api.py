"""Feedback/Grievance Agent — API tests. Uses a curated seed scheme (issuing_authority in
Mongo) to verify department resolution, and an unknown scheme to verify the honest "no
department found" path (Section 7.3/11)."""

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


async def test_admin_can_list_all_grievances(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    await client.post(
        "/api/grievances",
        json={"citizen_id": citizen_id, "category": "general", "description": "First ticket"},
    )
    await client.post(
        "/api/grievances",
        json={"citizen_id": citizen_id, "category": "delay", "description": "Second ticket"},
    )

    res = await client.get("/api/grievances", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    assert len(res.json()) == 2


async def test_non_admin_cannot_list_all_grievances(client, db):
    res = await client.get("/api/grievances")
    assert res.status_code in (401, 403)


async def test_admin_can_resolve_grievance(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    created = await client.post(
        "/api/grievances",
        json={"citizen_id": citizen_id, "category": "general", "description": "text"},
    )
    grievance_id = created.json()["id"]

    res = await client.post(
        f"/api/grievances/{grievance_id}/resolve",
        json={"resolution_note": "Contacted the department; issue resolved."},
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "resolved"
    assert body["resolution_note"] == "Contacted the department; issue resolved."
    assert body["resolved_at"] is not None


async def test_cannot_resolve_already_resolved_grievance(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    created = await client.post(
        "/api/grievances",
        json={"citizen_id": citizen_id, "category": "general", "description": "text"},
    )
    grievance_id = created.json()["id"]
    await client.post(
        f"/api/grievances/{grievance_id}/resolve", json={"resolution_note": "Done."}, headers=ADMIN_HEADERS
    )

    res = await client.post(
        f"/api/grievances/{grievance_id}/resolve", json={"resolution_note": "Again."}, headers=ADMIN_HEADERS
    )
    assert res.status_code == 400


async def test_non_admin_cannot_resolve_grievance(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    created = await client.post(
        "/api/grievances",
        json={"citizen_id": citizen_id, "category": "general", "description": "text"},
    )
    grievance_id = created.json()["id"]

    res = await client.post(f"/api/grievances/{grievance_id}/resolve", json={"resolution_note": "x"})
    assert res.status_code in (401, 403)
