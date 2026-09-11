"""Deadline/Reminder Agent — API tests. No GEMINI_API_KEY in the test env, so
retrieve_deadlines degrades to verified=False (app/rag/policy_service.py's BR-010-style
fallback) rather than raising — reminders must still be creatable with consent, just honestly
labeled as having no verified deadline."""

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


async def test_create_reminder_requires_consent(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)

    res = await client.post(
        "/api/reminders", json={"citizen_id": citizen_id, "scheme_id": scheme_id, "consent": False}
    )
    assert res.status_code == 422


async def test_create_reminder_with_consent_never_claims_sent(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)

    res = await client.post(
        "/api/reminders", json={"citizen_id": citizen_id, "scheme_id": scheme_id, "consent": True}
    )
    assert res.status_code == 201
    body = res.json()
    assert body["notification_sent"] is False
    assert body["status"] == "scheduled_internal"
    assert body["consent_given"] is True


async def test_create_reminder_citizen_not_found(client, db):
    await seed_schemes_if_empty(db)
    scheme_id = await _pm_kisan_scheme_id(db)
    res = await client.post(
        "/api/reminders",
        json={"citizen_id": "64b7f0000000000000000000", "scheme_id": scheme_id, "consent": True},
    )
    assert res.status_code == 404


async def test_list_reminders_for_citizen(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)
    scheme_id = await _pm_kisan_scheme_id(db)
    await client.post("/api/reminders", json={"citizen_id": citizen_id, "scheme_id": scheme_id, "consent": True})

    res = await client.get(f"/api/reminders/{citizen_id}")
    assert res.status_code == 200
    assert len(res.json()) == 1
