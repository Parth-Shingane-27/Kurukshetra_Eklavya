"""Citizen-reported scheme data-quality issues — distinct from FR-015's RAG candidate queue;
a raw citizen claim, never auto-applied to `schemes`."""

from app.core.config import get_settings

ADMIN_HEADERS = {"X-Admin-Token": get_settings().admin_credential}


async def _create_scheme(client, name="Report Test Scheme"):
    res = await client.post(
        "/api/schemes",
        json={"name": name, "category": "Agriculture,Rural & Environment", "benefit_type": "cash_transfer", "benefit_value_estimate": 1},
        headers=ADMIN_HEADERS,
    )
    return res.json()["id"]


async def test_create_report_anonymous(client):
    scheme_id = await _create_scheme(client)
    res = await client.post(
        "/api/scheme-reports",
        json={"scheme_id": scheme_id, "reason": "Outdated benefit amount", "comment": "It's actually higher now."},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "open"
    assert body["citizen_id"] is None
    assert body["scheme_name"] == "Report Test Scheme"


async def test_create_report_unknown_scheme_404s(client):
    res = await client.post(
        "/api/scheme-reports", json={"scheme_id": "000000000000000000000000", "reason": "test"}
    )
    assert res.status_code == 404


async def test_create_report_blank_reason_422s(client):
    scheme_id = await _create_scheme(client)
    res = await client.post("/api/scheme-reports", json={"scheme_id": scheme_id, "reason": "   "})
    assert res.status_code == 422


async def test_non_admin_cannot_list_reports(client):
    res = await client.get("/api/scheme-reports")
    assert res.status_code in (401, 403)


async def test_admin_can_list_and_resolve_report(client):
    scheme_id = await _create_scheme(client)
    created = await client.post("/api/scheme-reports", json={"scheme_id": scheme_id, "reason": "test"})
    report_id = created.json()["id"]

    listed = await client.get("/api/scheme-reports", headers=ADMIN_HEADERS)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    resolved = await client.post(
        f"/api/scheme-reports/{report_id}/resolve",
        json={"status": "addressed", "admin_notes": "Corrected the benefit amount."},
        headers=ADMIN_HEADERS,
    )
    assert resolved.status_code == 200
    body = resolved.json()
    assert body["status"] == "addressed"
    assert body["admin_notes"] == "Corrected the benefit amount."
    assert body["resolved_at"] is not None


async def test_cannot_resolve_already_resolved_report(client):
    scheme_id = await _create_scheme(client)
    created = await client.post("/api/scheme-reports", json={"scheme_id": scheme_id, "reason": "test"})
    report_id = created.json()["id"]
    await client.post(f"/api/scheme-reports/{report_id}/resolve", json={"status": "dismissed"}, headers=ADMIN_HEADERS)

    res = await client.post(f"/api/scheme-reports/{report_id}/resolve", json={"status": "addressed"}, headers=ADMIN_HEADERS)
    assert res.status_code == 400


async def test_resolve_rejects_open_status(client):
    scheme_id = await _create_scheme(client)
    created = await client.post("/api/scheme-reports", json={"scheme_id": scheme_id, "reason": "test"})
    report_id = created.json()["id"]

    res = await client.post(f"/api/scheme-reports/{report_id}/resolve", json={"status": "open"}, headers=ADMIN_HEADERS)
    assert res.status_code == 422


async def test_list_filters_by_status(client):
    scheme_id = await _create_scheme(client)
    created = await client.post("/api/scheme-reports", json={"scheme_id": scheme_id, "reason": "test"})
    await client.post(
        f"/api/scheme-reports/{created.json()['id']}/resolve", json={"status": "dismissed"}, headers=ADMIN_HEADERS
    )
    await client.post("/api/scheme-reports", json={"scheme_id": scheme_id, "reason": "another"})

    open_res = await client.get("/api/scheme-reports", params={"status": "open"}, headers=ADMIN_HEADERS)
    assert len(open_res.json()) == 1
    dismissed_res = await client.get("/api/scheme-reports", params={"status": "dismissed"}, headers=ADMIN_HEADERS)
    assert len(dismissed_res.json()) == 1
