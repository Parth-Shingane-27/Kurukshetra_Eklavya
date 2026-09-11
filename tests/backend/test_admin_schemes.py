"""FR-011 — Admin Scheme Knowledge Base management (TC-022, TC-023)."""

from app.core.config import get_settings
from app.modules.scheme_kb.service import seed_schemes_if_empty

ADMIN_HEADERS = {"X-Admin-Token": get_settings().admin_credential}

VALID_SCHEME = {
    "name": "Test Widow Pension Scheme",
    "category": "Social welfare & Empowerment",
    "benefit_type": "monthly_pension",
    "benefit_value_estimate": 5000,
    "rules": [{"field_name": "marital_status", "operator": "=", "value": "widowed"}],
    "document_requirements": [{"document_type": "Aadhaar Card", "is_mandatory": True}],
}


async def test_create_scheme_requires_admin_token(client):
    res = await client.post("/api/schemes", json=VALID_SCHEME)
    assert res.status_code == 401


async def test_create_scheme_rejects_wrong_token(client):
    res = await client.post("/api/schemes", json=VALID_SCHEME, headers={"X-Admin-Token": "wrong"})
    assert res.status_code == 401


async def test_create_scheme_valid(client):
    res = await client.post("/api/schemes", json=VALID_SCHEME, headers=ADMIN_HEADERS)
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "Test Widow Pension Scheme"
    assert body["is_active"] is True

    listed = await client.get("/api/schemes")
    assert any(s["name"] == "Test Widow Pension Scheme" for s in listed.json())


async def test_create_scheme_rejects_unsupported_operator(client):
    payload = {**VALID_SCHEME, "rules": [{"field_name": "age", "operator": "!=", "value": 18}]}
    res = await client.post("/api/schemes", json=payload, headers=ADMIN_HEADERS)
    assert res.status_code == 422


async def test_create_scheme_rejects_in_operator_with_scalar_value(client):
    payload = {**VALID_SCHEME, "rules": [{"field_name": "social_category", "operator": "in", "value": "SC"}]}
    res = await client.post("/api/schemes", json=payload, headers=ADMIN_HEADERS)
    assert res.status_code == 422


async def test_create_scheme_rejects_equality_operator_with_list_value(client):
    payload = {**VALID_SCHEME, "rules": [{"field_name": "state", "operator": "=", "value": ["A", "B"]}]}
    res = await client.post("/api/schemes", json=payload, headers=ADMIN_HEADERS)
    assert res.status_code == 422


async def test_create_scheme_rejects_blank_field_name(client):
    payload = {**VALID_SCHEME, "rules": [{"field_name": "  ", "operator": "=", "value": "x"}]}
    res = await client.post("/api/schemes", json=payload, headers=ADMIN_HEADERS)
    assert res.status_code == 422


async def test_create_scheme_rejects_blank_document_type(client):
    payload = {**VALID_SCHEME, "document_requirements": [{"document_type": "", "is_mandatory": True}]}
    res = await client.post("/api/schemes", json=payload, headers=ADMIN_HEADERS)
    assert res.status_code == 422


async def test_deactivate_scheme_requires_admin_token(client):
    created = await client.post("/api/schemes", json=VALID_SCHEME, headers=ADMIN_HEADERS)
    scheme_id = created.json()["id"]
    res = await client.put(f"/api/schemes/{scheme_id}", json={"is_active": False})
    assert res.status_code == 401


async def test_deactivate_scheme_excludes_it_from_default_listing(client):
    created = await client.post("/api/schemes", json=VALID_SCHEME, headers=ADMIN_HEADERS)
    scheme_id = created.json()["id"]

    res = await client.put(f"/api/schemes/{scheme_id}", json={"is_active": False}, headers=ADMIN_HEADERS)
    assert res.status_code == 200
    assert res.json()["is_active"] is False

    active_only = await client.get("/api/schemes")
    assert scheme_id not in {s["id"] for s in active_only.json()}

    with_inactive = await client.get("/api/schemes", params={"include_inactive": "true"})
    assert scheme_id in {s["id"] for s in with_inactive.json()}


async def test_update_scheme_not_found(client):
    res = await client.put(
        "/api/schemes/64b7f0000000000000000000", json={"is_active": False}, headers=ADMIN_HEADERS
    )
    assert res.status_code == 404


async def test_scheme_application_link_surfaces_in_eligibility_results(client):
    scheme = {**VALID_SCHEME, "application_link": "https://example.gov.in/apply/widow-pension"}
    await client.post("/api/schemes", json=scheme, headers=ADMIN_HEADERS)

    citizen_res = await client.post(
        "/api/citizens",
        json={
            "name": "Link Test",
            "date_of_birth": "1970-01-01",
            "state": "Bihar",
            "district": "Patna",
            "marital_status": "widowed",
        },
    )
    citizen_id = citizen_res.json()["id"]

    eval_res = await client.post("/api/eligibility/evaluate", json={"citizen_id": citizen_id})
    assert eval_res.status_code == 200
    result = next(r for r in eval_res.json()["results"] if r["scheme_name"] == "Test Widow Pension Scheme")
    assert result["status"] == "eligible"
    assert result["application_link"] == "https://example.gov.in/apply/widow-pension"


async def test_admin_created_scheme_affects_subsequent_evaluation(client, db):
    """Phase 7 completion criteria: 'Curator can add a new scheme through the UI and see it
    affect subsequent evaluations' — without redeploying code (NFR-005)."""
    await seed_schemes_if_empty(db)
    citizen_res = await client.post(
        "/api/citizens",
        json={
            "name": "Widow Test",
            "date_of_birth": "1970-01-01",
            "state": "Bihar",
            "district": "Patna",
            "marital_status": "widowed",
        },
    )
    citizen_id = citizen_res.json()["id"]

    await client.post("/api/schemes", json=VALID_SCHEME, headers=ADMIN_HEADERS)

    eval_res = await client.post("/api/eligibility/evaluate", json={"citizen_id": citizen_id})
    assert eval_res.status_code == 200
    result = next(r for r in eval_res.json()["results"] if r["scheme_name"] == "Test Widow Pension Scheme")
    assert result["status"] == "eligible"
