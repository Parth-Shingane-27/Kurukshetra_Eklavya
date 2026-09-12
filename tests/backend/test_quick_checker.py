"""FR-013 — Quick Scheme Eligibility Checker (BR-014: stateless, no citizen account)."""

from app.core.config import get_settings

ADMIN_HEADERS = {"X-Admin-Token": get_settings().admin_credential}

SCHEME = {
    "name": "Quick Check Test Widow Pension",
    "category": "Social welfare & Empowerment",
    "benefit_type": "monthly_pension",
    "benefit_value_estimate": 5000,
    "rules": [{"field_name": "marital_status", "operator": "=", "value": "widowed"}],
    "document_requirements": [{"document_type": "Aadhaar Card", "is_mandatory": True}],
    "links": {"application_url": "https://example.gov.in/apply", "application_link_status": "verified"},
}

OTHER_SCHEME_SAME_CATEGORY = {
    "name": "Quick Check Test Disability Pension",
    "category": "Social welfare & Empowerment",
    "benefit_type": "monthly_pension",
    "benefit_value_estimate": 4000,
    "rules": [{"field_name": "disability_status", "operator": "=", "value": True}],
    "document_requirements": [],
}


async def _create_scheme(client, scheme):
    res = await client.post("/api/schemes", json=scheme, headers=ADMIN_HEADERS)
    assert res.status_code == 201
    return res.json()["id"]


async def test_quick_check_eligible(client):
    scheme_id = await _create_scheme(client, SCHEME)
    res = await client.post("/api/quick-check", json={"scheme_id": scheme_id, "criteria": {"marital_status": "widowed"}})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "eligible"
    assert body["application_url"] == "https://example.gov.in/apply"
    assert body["application_link_status"] == "verified"
    assert body["required_documents"] == ["Aadhaar Card"]
    assert body["suggested_alternatives"] == []
    assert "preliminary self-assessment" in body["disclaimer"]


async def test_quick_check_not_eligible_suggests_same_category_alternatives(client):
    scheme_id = await _create_scheme(client, SCHEME)
    await _create_scheme(client, OTHER_SCHEME_SAME_CATEGORY)

    res = await client.post("/api/quick-check", json={"scheme_id": scheme_id, "criteria": {"marital_status": "married"}})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "not_eligible"
    alt_names = {a["scheme_name"] for a in body["suggested_alternatives"]}
    assert "Quick Check Test Disability Pension" in alt_names
    assert "Quick Check Test Widow Pension" not in alt_names  # never suggests itself


async def test_quick_check_indeterminate_when_criteria_missing(client):
    scheme_id = await _create_scheme(client, SCHEME)
    res = await client.post("/api/quick-check", json={"scheme_id": scheme_id, "criteria": {}})
    assert res.status_code == 200
    assert res.json()["status"] == "indeterminate"


async def test_quick_check_accepts_date_of_birth_and_derives_age(client):
    scheme = {
        **SCHEME,
        "name": "Quick Check Age Scheme",
        "rules": [{"field_name": "age", "operator": ">=", "value": 60}],
    }
    scheme_id = await _create_scheme(client, scheme)
    res = await client.post(
        "/api/quick-check", json={"scheme_id": scheme_id, "criteria": {"date_of_birth": "1950-01-01"}}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "eligible"


async def test_quick_check_unknown_scheme_404s(client):
    res = await client.post(
        "/api/quick-check", json={"scheme_id": "64b7f0000000000000000000", "criteria": {}}
    )
    assert res.status_code == 404


async def test_quick_check_inactive_scheme_404s(client):
    scheme_id = await _create_scheme(client, SCHEME)
    await client.put(f"/api/schemes/{scheme_id}", json={"is_active": False}, headers=ADMIN_HEADERS)
    res = await client.post("/api/quick-check", json={"scheme_id": scheme_id, "criteria": {"marital_status": "widowed"}})
    assert res.status_code == 404


async def test_quick_check_is_stateless(client, db):
    """BR-014: no citizen record, no eligibility_results row, nothing persisted beyond the
    request/response cycle."""
    scheme_id = await _create_scheme(client, SCHEME)
    citizens_before = await db.citizens.count_documents({})
    eligibility_before = await db.eligibility_results.count_documents({})

    res = await client.post("/api/quick-check", json={"scheme_id": scheme_id, "criteria": {"marital_status": "widowed"}})
    assert res.status_code == 200

    assert await db.citizens.count_documents({}) == citizens_before
    assert await db.eligibility_results.count_documents({}) == eligibility_before


async def test_quick_check_requires_no_authentication(client):
    """FR-013: usable with zero account/login friction."""
    scheme_id = await _create_scheme(client, SCHEME)
    res = await client.post("/api/quick-check", json={"scheme_id": scheme_id, "criteria": {"marital_status": "widowed"}})
    assert res.status_code == 200
