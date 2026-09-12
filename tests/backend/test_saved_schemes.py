"""Saved/watchlist schemes — bookmarking independent of eligibility."""

from app.core.config import get_settings

ADMIN_HEADERS = {"X-Admin-Token": get_settings().admin_credential}
BASE_CITIZEN = {"name": "Saved Test", "date_of_birth": "1990-01-01", "state": "Bihar", "district": "Patna"}


async def _create_citizen(client, headers=None):
    res = await client.post("/api/citizens", json=BASE_CITIZEN, headers=headers or {})
    return res.json()["id"]


async def _create_scheme(client, name="Saved Test Scheme"):
    res = await client.post(
        "/api/schemes",
        json={"name": name, "category": "Agriculture,Rural & Environment", "benefit_type": "cash_transfer", "benefit_value_estimate": 1},
        headers=ADMIN_HEADERS,
    )
    return res.json()["id"]


async def test_save_and_list_scheme(client):
    citizen_id = await _create_citizen(client)
    scheme_id = await _create_scheme(client)

    res = await client.post(f"/api/citizens/{citizen_id}/saved-schemes", json={"scheme_id": scheme_id})
    assert res.status_code == 201
    assert res.json()["scheme_name"] == "Saved Test Scheme"

    listed = await client.get(f"/api/citizens/{citizen_id}/saved-schemes")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


async def test_saving_the_same_scheme_twice_is_idempotent(client):
    citizen_id = await _create_citizen(client)
    scheme_id = await _create_scheme(client)

    await client.post(f"/api/citizens/{citizen_id}/saved-schemes", json={"scheme_id": scheme_id})
    await client.post(f"/api/citizens/{citizen_id}/saved-schemes", json={"scheme_id": scheme_id})

    listed = await client.get(f"/api/citizens/{citizen_id}/saved-schemes")
    assert len(listed.json()) == 1


async def test_unsave_scheme(client):
    citizen_id = await _create_citizen(client)
    scheme_id = await _create_scheme(client)
    await client.post(f"/api/citizens/{citizen_id}/saved-schemes", json={"scheme_id": scheme_id})

    del_res = await client.delete(f"/api/citizens/{citizen_id}/saved-schemes/{scheme_id}")
    assert del_res.status_code == 204

    listed = await client.get(f"/api/citizens/{citizen_id}/saved-schemes")
    assert listed.json() == []


async def test_unsave_unknown_returns_404(client):
    citizen_id = await _create_citizen(client)
    scheme_id = await _create_scheme(client)
    res = await client.delete(f"/api/citizens/{citizen_id}/saved-schemes/{scheme_id}")
    assert res.status_code == 404


async def test_save_unknown_scheme_returns_404(client):
    citizen_id = await _create_citizen(client)
    res = await client.post(
        f"/api/citizens/{citizen_id}/saved-schemes", json={"scheme_id": "000000000000000000000000"}
    )
    assert res.status_code == 404


async def test_non_owner_cannot_access_saved_schemes(client):
    async def _login(email):
        payload = {"email": email, "password": "s3cret-pass", "role": "citizen"}
        await client.post("/api/auth/register", json=payload)
        login_res = await client.post("/api/auth/login", json={"email": email, "password": "s3cret-pass"})
        return login_res.json()

    owner = await _login("saved-owner@example.com")
    other = await _login("saved-other@example.com")
    owner_headers = {"Authorization": f"Bearer {owner['access_token']}"}
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}

    citizen_id = await _create_citizen(client, headers=owner_headers)
    res = await client.get(f"/api/citizens/{citizen_id}/saved-schemes", headers=other_headers)
    assert res.status_code == 403
