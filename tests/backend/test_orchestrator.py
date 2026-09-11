"""Agent Orchestrator: POST /api/agent/run, GET /api/agent/trace/:citizenId (FR-010, BR-012; TC-021)."""

from app.modules.scheme_kb.service import seed_schemes_if_empty

BASE_CITIZEN = {
    "name": "Test Citizen",
    "date_of_birth": "1975-04-20",
    "state": "Maharashtra",
    "district": "Pune",
}


async def _create_citizen(client, **overrides):
    payload = {**BASE_CITIZEN, **overrides}
    res = await client.post("/api/citizens", json=payload)
    assert res.status_code == 201
    return res.json()["id"]


async def test_run_pipeline_end_to_end(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client, bpl_status=True, annual_income=200000)

    res = await client.post("/api/agent/run", json={"citizen_id": citizen_id})
    assert res.status_code == 200
    body = res.json()

    assert body["citizen_id"] == citizen_id
    assert any(r["status"] == "eligible" for r in body["eligibility"]["results"])
    assert len(body["conflicts"]["conflicts"]) == 1
    assert body["bundle"]["scheme_ids"]
    assert body["bundle"]["explanation_text"]
    assert body["checklist"]["checklist_items"]


async def test_trace_records_all_five_stages_in_order(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client, bpl_status=True, annual_income=200000)
    await client.post("/api/agent/run", json={"citizen_id": citizen_id})

    res = await client.get(f"/api/agent/trace/{citizen_id}")
    assert res.status_code == 200
    steps = res.json()["steps"]
    assert [s["step_name"] for s in steps] == [
        "eligibility",
        "conflicts",
        "bundle_optimization",
        "explanation",
        "checklist",
    ]
    timestamps = [s["created_at"] for s in steps]
    assert timestamps == sorted(timestamps)


async def test_trace_empty_before_any_run(client, db):
    citizen_id = await _create_citizen(client)
    res = await client.get(f"/api/agent/trace/{citizen_id}")
    assert res.status_code == 200
    assert res.json()["steps"] == []


async def test_trace_citizen_not_found(client):
    res = await client.get("/api/agent/trace/64b7f0000000000000000000")
    assert res.status_code == 404


async def test_run_pipeline_citizen_not_found(client, db):
    await seed_schemes_if_empty(db)
    res = await client.post("/api/agent/run", json={"citizen_id": "64b7f0000000000000000000"})
    assert res.status_code == 404


async def test_run_pipeline_failure_logs_partial_trace_and_reraises(client, db):
    await seed_schemes_if_empty(db)
    # Only required fields set -> every seeded scheme is indeterminate -> 409 at stage 1.
    citizen_id = await _create_citizen(client)

    res = await client.post("/api/agent/run", json={"citizen_id": citizen_id})
    assert res.status_code == 409

    trace = await client.get(f"/api/agent/trace/{citizen_id}")
    steps = trace.json()["steps"]
    assert [s["step_name"] for s in steps] == ["eligibility"]
    assert "error" in steps[0]["output_snapshot"]


async def test_input_snapshot_captures_citizen_profile_for_eligibility_stage(client, db):
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client, occupation="farmer", land_holding_acres=3)
    await client.post("/api/agent/run", json={"citizen_id": citizen_id})

    trace = await client.get(f"/api/agent/trace/{citizen_id}")
    eligibility_step = trace.json()["steps"][0]
    assert eligibility_step["input_snapshot"]["occupation"] == "farmer"


async def test_trace_populates_from_individual_endpoint_calls_without_agent_run(client, db):
    """The frontend drives each screen through its own endpoint (matching Section 17's
    per-screen loading states), never calling /api/agent/run directly. The trace must still
    populate from those direct calls, or the Trace screen would always be empty in normal use.
    """
    await seed_schemes_if_empty(db)
    citizen_id = await _create_citizen(client, bpl_status=True, annual_income=200000)

    await client.post("/api/eligibility/evaluate", json={"citizen_id": citizen_id})
    await client.post("/api/conflicts/detect", json={"citizen_id": citizen_id})
    bundle_res = await client.post("/api/bundle/optimize", json={"citizen_id": citizen_id})
    bundle_id = bundle_res.json()["bundle_id"]
    await client.post("/api/checklist/generate", json={"bundle_id": bundle_id})

    trace = await client.get(f"/api/agent/trace/{citizen_id}")
    steps = trace.json()["steps"]
    assert [s["step_name"] for s in steps] == [
        "eligibility",
        "conflicts",
        "bundle_optimization",
        "explanation",
        "checklist",
    ]
