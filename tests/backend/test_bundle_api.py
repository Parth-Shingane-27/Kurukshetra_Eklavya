"""FR-005/FR-006 — POST /api/conflicts/detect, POST /api/bundle/optimize, GET /api/bundle/:id."""

from app.modules.scheme_kb.service import seed_schemes_if_empty

BASE_CITIZEN = {
    "name": "Test Citizen",
    "date_of_birth": "1990-01-01",
    "state": "Maharashtra",
    "district": "Pune",
}


async def _create_citizen(client, **overrides):
    payload = {**BASE_CITIZEN, **overrides}
    res = await client.post("/api/citizens", json=payload)
    assert res.status_code == 201
    return res.json()["id"]


async def _evaluate(client, citizen_id):
    res = await client.post("/api/eligibility/evaluate", json={"citizen_id": citizen_id})
    assert res.status_code == 200
    return res.json()


async def test_conflict_group_pair_detected(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client, bpl_status=True, annual_income=200000)
    await _evaluate(client, citizen_id)

    res = await client.post("/api/conflicts/detect", json={"citizen_id": citizen_id})
    assert res.status_code == 200
    conflicts = res.json()["conflicts"]
    housing_conflicts = [c for c in conflicts if c["conflict_type"] == "conflict_group"]
    assert len(housing_conflicts) == 1
    names = {housing_conflicts[0]["scheme_a_name"], housing_conflicts[0]["scheme_b_name"]}
    assert names == {"Pradhan Mantri Awas Yojana (Rural)", "State Rural Housing Assistance Scheme"}


async def test_mutually_exclusive_pair_detected(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(
        client, date_of_birth="2000-01-01", employment_status="unemployed", education_level="undergraduate"
    )
    await _evaluate(client, citizen_id)

    res = await client.post("/api/conflicts/detect", json={"citizen_id": citizen_id})
    conflicts = res.json()["conflicts"]
    direct = [c for c in conflicts if c["conflict_type"] == "mutually_exclusive"]
    assert len(direct) == 1
    names = {direct[0]["scheme_a_name"], direct[0]["scheme_b_name"]}
    assert names == {"Skill Development Training Stipend", "State Unemployment Allowance Scheme"}


async def test_bundle_optimize_picks_higher_value_housing_scheme(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client, bpl_status=True, annual_income=200000)
    await _evaluate(client, citizen_id)

    res = await client.post("/api/bundle/optimize", json={"citizen_id": citizen_id})
    assert res.status_code == 200
    body = res.json()

    pmay = await db.schemes.find_one({"name": "Pradhan Mantri Awas Yojana (Rural)"})
    state_housing = await db.schemes.find_one({"name": "State Rural Housing Assistance Scheme"})
    assert str(pmay["_id"]) in body["scheme_ids"]
    assert str(state_housing["_id"]) not in body["scheme_ids"]

    excluded_ids = {e["scheme_id"] for e in body["excluded"]}
    assert str(state_housing["_id"]) in excluded_ids
    assert body["policy_citations"] is None  # no GEMINI_API_KEY configured in the test env


async def test_bundle_optimize_attaches_policy_citations_when_rag_configured(client, db, monkeypatch):
    """Section 6: Explanation Agent grounding — best-effort only, wired through
    app.rag.citations.attach_policy_citations, never touching the real vector store in tests."""
    from app.rag.schemas import RetrievalResult, RetrievedEvidence

    class FakeSettings:
        gemini_api_key = "fake-key-for-this-test-only"

    class FakePolicyService:
        async def retrieve_policy_evidence(self, query, top_k=1, filters=None):
            return RetrievalResult(
                query=query,
                verified=True,
                evidence=[
                    RetrievedEvidence(
                        content=f"Sample retrieved evidence for {query}",
                        scheme_id="corpus-999",
                        scheme_name=query,
                        section="details",
                        source="dataset_provided",
                    )
                ],
            )

    monkeypatch.setattr("app.rag.citations.get_settings", lambda: FakeSettings())
    monkeypatch.setattr("app.rag.citations.get_policy_service", lambda: FakePolicyService())

    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client, bpl_status=True, annual_income=200000)
    await _evaluate(client, citizen_id)

    res = await client.post("/api/bundle/optimize", json={"citizen_id": citizen_id})
    assert res.status_code == 200
    body = res.json()

    assert body["policy_citations"] is not None
    cited_names = {c["scheme_name"] for c in body["policy_citations"]}
    assert cited_names  # at least one included scheme got a citation
    for citation in body["policy_citations"]:
        assert citation["evidence"][0]["source"] == "dataset_provided"


async def test_bundle_optimize_no_eligible_schemes_is_empty_not_error(client, db):
    await seed_schemes_if_empty(db)
    # Every field set so every scheme resolves definitively to not_eligible.
    citizen_id = await _create_citizen(
        client,
        occupation="salaried",
        land_holding_acres=50,
        bpl_status=False,
        annual_income=900000,
        social_category="General",
        education_level="none",
        disability_status=False,
        employment_status="employed",
    )
    eval_result = await _evaluate(client, citizen_id)
    assert all(r["status"] == "not_eligible" for r in eval_result["results"])

    res = await client.post("/api/bundle/optimize", json={"citizen_id": citizen_id})
    assert res.status_code == 200
    body = res.json()
    assert body["scheme_ids"] == []
    assert body["total_benefit_value"] == 0
    assert body["excluded"] == []


async def test_bundle_optimize_requires_eligibility_evaluated_first(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client)  # no /api/eligibility/evaluate call yet

    res = await client.post("/api/bundle/optimize", json={"citizen_id": citizen_id})
    assert res.status_code == 422


async def test_bundle_optimize_citizen_not_found(client, db):
    await seed_schemes_if_empty(db)
    res = await client.post(
        "/api/bundle/optimize", json={"citizen_id": "64b7f0000000000000000000"}
    )
    assert res.status_code == 404


async def test_get_bundle_round_trip(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client, bpl_status=True, annual_income=200000)
    await _evaluate(client, citizen_id)
    created = await client.post("/api/bundle/optimize", json={"citizen_id": citizen_id})
    bundle_id = created.json()["bundle_id"]

    res = await client.get(f"/api/bundle/{bundle_id}")
    assert res.status_code == 200
    assert res.json()["bundle_id"] == bundle_id
    assert res.json()["scheme_ids"] == created.json()["scheme_ids"]


async def test_get_bundle_not_found(client):
    res = await client.get("/api/bundle/64b7f0000000000000000000")
    assert res.status_code == 404
