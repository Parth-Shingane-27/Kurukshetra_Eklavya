"""In-app Notification Center — real events only (grievance created/resolved, reminders),
never a fabricated/scheduled push."""

from app.core.config import get_settings

ADMIN_HEADERS = {"X-Admin-Token": get_settings().admin_credential}

BASE_CITIZEN = {"name": "Notif Test", "date_of_birth": "1990-01-01", "state": "Bihar", "district": "Patna"}


async def _create_citizen(client):
    res = await client.post("/api/citizens", json=BASE_CITIZEN)
    return res.json()["id"]


async def test_grievance_created_produces_a_notification(client):
    citizen_id = await _create_citizen(client)
    await client.post(
        "/api/grievances", json={"citizen_id": citizen_id, "category": "general", "description": "text"}
    )

    res = await client.get(f"/api/citizens/{citizen_id}/notifications")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["type"] == "grievance_created"
    assert body[0]["read"] is False


async def test_grievance_resolved_produces_a_second_notification(client):
    citizen_id = await _create_citizen(client)
    created = await client.post(
        "/api/grievances", json={"citizen_id": citizen_id, "category": "general", "description": "text"}
    )
    grievance_id = created.json()["id"]

    await client.post(
        f"/api/grievances/{grievance_id}/resolve", json={"resolution_note": "Fixed."}, headers=ADMIN_HEADERS
    )

    res = await client.get(f"/api/citizens/{citizen_id}/notifications")
    body = res.json()
    assert len(body) == 2
    types = {n["type"] for n in body}
    assert types == {"grievance_created", "grievance_resolved"}


async def test_unread_count_and_mark_read(client):
    citizen_id = await _create_citizen(client)
    await client.post(
        "/api/grievances", json={"citizen_id": citizen_id, "category": "general", "description": "text"}
    )

    count_res = await client.get(f"/api/citizens/{citizen_id}/notifications/unread-count")
    assert count_res.json()["unread_count"] == 1

    listed = await client.get(f"/api/citizens/{citizen_id}/notifications")
    notification_id = listed.json()[0]["id"]

    mark_res = await client.post(f"/api/citizens/{citizen_id}/notifications/{notification_id}/read")
    assert mark_res.status_code == 200
    assert mark_res.json()["read"] is True

    count_res2 = await client.get(f"/api/citizens/{citizen_id}/notifications/unread-count")
    assert count_res2.json()["unread_count"] == 0


async def test_reminder_appears_in_notification_feed(client, db):
    citizen_id = await _create_citizen(client)
    scheme_res = await client.post(
        "/api/schemes",
        json={"name": "Notif Test Scheme", "category": "Agriculture,Rural & Environment", "benefit_type": "cash_transfer", "benefit_value_estimate": 1},
        headers=ADMIN_HEADERS,
    )
    scheme_id = scheme_res.json()["id"]

    await client.post(
        "/api/reminders", json={"citizen_id": citizen_id, "scheme_id": scheme_id, "consent": True}
    )

    res = await client.get(f"/api/citizens/{citizen_id}/notifications")
    body = res.json()
    assert any(n["type"] == "deadline_reminder" for n in body)


async def test_cannot_mark_reminder_derived_notification_as_read(client):
    citizen_id = await _create_citizen(client)
    scheme_res = await client.post(
        "/api/schemes",
        json={"name": "Notif Test Scheme 2", "category": "Agriculture,Rural & Environment", "benefit_type": "cash_transfer", "benefit_value_estimate": 1},
        headers=ADMIN_HEADERS,
    )
    scheme_id = scheme_res.json()["id"]
    await client.post("/api/reminders", json={"citizen_id": citizen_id, "scheme_id": scheme_id, "consent": True})

    listed = await client.get(f"/api/citizens/{citizen_id}/notifications")
    reminder_notification_id = next(n["id"] for n in listed.json() if n["type"] == "deadline_reminder")

    res = await client.post(f"/api/citizens/{citizen_id}/notifications/{reminder_notification_id}/read")
    assert res.status_code == 400


async def test_non_owner_cannot_read_another_citizens_notifications(client):
    async def _login(email):
        payload = {"email": email, "password": "s3cret-pass", "role": "citizen"}
        await client.post("/api/auth/register", json=payload)
        login_res = await client.post("/api/auth/login", json={"email": email, "password": "s3cret-pass"})
        return login_res.json()

    owner = await _login("notif-owner@example.com")
    other = await _login("notif-other@example.com")
    owner_headers = {"Authorization": f"Bearer {owner['access_token']}"}
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}

    citizen_res = await client.post("/api/citizens", json=BASE_CITIZEN, headers=owner_headers)
    citizen_id = citizen_res.json()["id"]

    res = await client.get(f"/api/citizens/{citizen_id}/notifications", headers=other_headers)
    assert res.status_code == 403

    ok_res = await client.get(f"/api/citizens/{citizen_id}/notifications", headers=owner_headers)
    assert ok_res.status_code == 200
