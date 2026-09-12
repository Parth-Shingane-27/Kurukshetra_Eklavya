"""Admin analytics — real deterministic counts, no LLM, admin-only."""

from app.core.config import get_settings

ADMIN_HEADERS = {"X-Admin-Token": get_settings().admin_credential}
BASE_CITIZEN = {"name": "Analytics Test", "date_of_birth": "1990-01-01", "state": "Bihar", "district": "Patna"}


async def _create_citizen(client):
    res = await client.post("/api/citizens", json=BASE_CITIZEN)
    return res.json()["id"]


async def _create_scheme(client, name, category="Agriculture,Rural & Environment"):
    res = await client.post(
        "/api/schemes",
        json={"name": name, "category": category, "benefit_type": "cash_transfer", "benefit_value_estimate": 1},
        headers=ADMIN_HEADERS,
    )
    return res.json()["id"]


async def test_non_admin_cannot_view_analytics(client):
    res = await client.get("/api/admin/analytics")
    assert res.status_code in (401, 403)


async def test_analytics_reflects_real_counts(client):
    citizen_id = await _create_citizen(client)
    scheme_id = await _create_scheme(client, "Analytics Test Scheme")
    await client.post(f"/api/citizens/{citizen_id}/saved-schemes", json={"scheme_id": scheme_id})
    await client.post(
        "/api/grievances", json={"citizen_id": citizen_id, "category": "general", "description": "text"}
    )

    res = await client.get("/api/admin/analytics", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    body = res.json()
    assert body["total_citizens"] >= 1
    assert body["total_active_schemes"] >= 1
    assert body["open_grievances"] >= 1
    assert any(s["scheme_name"] == "Analytics Test Scheme" for s in body["most_saved_schemes"])
    assert any(c["category"] == "Agriculture,Rural & Environment" for c in body["schemes_by_category"])
