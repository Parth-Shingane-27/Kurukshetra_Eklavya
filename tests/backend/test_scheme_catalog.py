"""FR-014 — Scheme Catalog Search with Form-Filling Guides."""

from app.core.config import get_settings

ADMIN_HEADERS = {"X-Admin-Token": get_settings().admin_credential}

SCHEME_WITH_GUIDE = {
    "name": "Catalog Test Farmer Support Grant",
    "description": "A grant for smallholder farmers to buy seeds and fertilizer.",
    "issuing_authority": "Ministry of Agriculture",
    "category": "Agriculture,Rural & Environment",
    "benefit_type": "cash_transfer",
    "benefit_value_estimate": 3000,
    "rules": [{"field_name": "occupation", "operator": "=", "value": "farmer"}],
    "document_requirements": [],
    "links": {"application_url": "https://example.gov.in/apply", "application_link_status": "verified"},
    "guide": {
        "guide_en": ["Visit the portal.", "Fill the form.", "Submit and note the reference number."],
        "guide_mr": ["पोर्टलला भेट द्या.", "फॉर्म भरा.", "सबमिट करा आणि संदर्भ क्रमांक नोंदवा."],
        "video_url": None,
    },
}

SCHEME_WITHOUT_GUIDE = {
    "name": "Catalog Test Widow Pension",
    "description": "Monthly pension for widowed persons.",
    "issuing_authority": "Ministry of Social Justice",
    "category": "Social welfare & Empowerment",
    "benefit_type": "monthly_pension",
    "benefit_value_estimate": 2000,
    "rules": [{"field_name": "marital_status", "operator": "=", "value": "widowed"}],
    "document_requirements": [],
}


async def _create_scheme(client, scheme):
    res = await client.post("/api/schemes", json=scheme, headers=ADMIN_HEADERS)
    assert res.status_code == 201
    return res.json()


async def test_search_catalog_by_keyword_matches_name(client):
    await _create_scheme(client, SCHEME_WITH_GUIDE)
    await _create_scheme(client, SCHEME_WITHOUT_GUIDE)

    res = await client.get("/api/catalog/schemes", params={"query": "Farmer Support"})
    assert res.status_code == 200
    names = [s["name"] for s in res.json()]
    assert "Catalog Test Farmer Support Grant" in names
    assert "Catalog Test Widow Pension" not in names


async def test_search_catalog_by_keyword_matches_description(client):
    await _create_scheme(client, SCHEME_WITH_GUIDE)

    res = await client.get("/api/catalog/schemes", params={"query": "seeds and fertilizer"})
    assert res.status_code == 200
    names = [s["name"] for s in res.json()]
    assert "Catalog Test Farmer Support Grant" in names


async def test_search_catalog_no_matches_is_empty_list_not_error(client):
    res = await client.get("/api/catalog/schemes", params={"query": "no such scheme exists anywhere xyz"})
    assert res.status_code == 200
    assert res.json() == []


async def test_search_catalog_combines_query_and_category_filter(client):
    await _create_scheme(client, SCHEME_WITH_GUIDE)
    await _create_scheme(client, SCHEME_WITHOUT_GUIDE)

    res = await client.get(
        "/api/catalog/schemes",
        params={"query": "Catalog Test", "category": "Social welfare & Empowerment"},
    )
    assert res.status_code == 200
    names = [s["name"] for s in res.json()]
    assert names == ["Catalog Test Widow Pension"]


async def test_get_guide_returns_authored_guide(client):
    created = await _create_scheme(client, SCHEME_WITH_GUIDE)

    res = await client.get(f"/api/catalog/schemes/{created['id']}/guide")
    assert res.status_code == 200
    body = res.json()
    assert body["scheme_name"] == "Catalog Test Farmer Support Grant"
    assert body["guide"]["guide_en"][0] == "Visit the portal."
    assert body["guide"]["guide_mr"][0] == "पोर्टलला भेट द्या."
    assert body["application_url"] == "https://example.gov.in/apply"


async def test_get_guide_returns_null_guide_when_none_authored(client):
    created = await _create_scheme(client, SCHEME_WITHOUT_GUIDE)

    res = await client.get(f"/api/catalog/schemes/{created['id']}/guide")
    assert res.status_code == 200
    body = res.json()
    assert body["guide"] is None


async def test_get_guide_unknown_scheme_returns_404(client):
    res = await client.get("/api/catalog/schemes/000000000000000000000000/guide")
    assert res.status_code == 404


async def test_catalog_search_requires_no_auth(client):
    res = await client.get("/api/catalog/schemes")
    assert res.status_code == 200
