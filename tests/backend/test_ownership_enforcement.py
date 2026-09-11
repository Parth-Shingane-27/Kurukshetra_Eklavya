"""Extends FR-016's owner-or-admin protection (BR-016) from citizens.py to the rest of the
pipeline: eligibility, conflicts, bundle, checklist, and agent endpoints."""

from app.core.config import get_settings
from app.modules.scheme_kb.service import seed_schemes_if_empty

ADMIN_BOOTSTRAP = {"admin_bootstrap_credential": get_settings().admin_credential}


async def _login(client, email, role="citizen"):
    payload = {"email": email, "password": "s3cret-pass", "role": role}
    if role == "admin":
        payload.update(ADMIN_BOOTSTRAP)
    await client.post("/api/auth/register", json=payload)
    login_res = await client.post("/api/auth/login", json={"email": email, "password": "s3cret-pass"})
    body = login_res.json()
    verify_res = await client.post(
        "/api/auth/verify-otp", json={"pending_token": body["pending_token"], "code": body["debug_otp"]}
    )
    return verify_res.json()


async def _make_owned_citizen(client, auth_headers):
    res = await client.post(
        "/api/citizens",
        json={
            "name": "Pipeline Owner",
            "date_of_birth": "1970-01-01",
            "state": "Bihar",
            "district": "Patna",
            "annual_income": 200000,
            "bpl_status": True,
        },
        headers=auth_headers,
    )
    return res.json()["id"]


async def test_anonymous_citizen_pipeline_still_fully_open(client, db):
    """Backward compatibility: an anonymously-created citizen's full pipeline stays reachable
    with no auth at all, exactly as before this change."""
    await seed_schemes_if_empty(db)
    res = await client.post(
        "/api/citizens",
        json={
            "name": "Anon Pipeline",
            "date_of_birth": "1970-01-01",
            "state": "Bihar",
            "district": "Patna",
            "bpl_status": True,
            "annual_income": 200000,
        },
    )
    citizen_id = res.json()["id"]

    assert (await client.post("/api/eligibility/evaluate", json={"citizen_id": citizen_id})).status_code == 200
    assert (await client.post("/api/conflicts/detect", json={"citizen_id": citizen_id})).status_code == 200
    bundle_res = await client.post("/api/bundle/optimize", json={"citizen_id": citizen_id})
    assert bundle_res.status_code == 200
    bundle_id = bundle_res.json()["bundle_id"]

    assert (await client.get(f"/api/bundle/{bundle_id}")).status_code == 200
    assert (await client.post("/api/checklist/generate", json={"bundle_id": bundle_id})).status_code == 200
    assert (await client.get(f"/api/checklist/{bundle_id}")).status_code == 200
    assert (await client.get(f"/api/agent/trace/{citizen_id}")).status_code == 200


async def test_owned_citizen_pipeline_rejects_stranger_and_allows_owner(client, db):
    await seed_schemes_if_empty(db)
    owner_tokens = await _login(client, "pipeline_owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_tokens['access_token']}"}
    citizen_id = await _make_owned_citizen(client, owner_headers)

    stranger_tokens = await _login(client, "pipeline_stranger@example.com")
    stranger_headers = {"Authorization": f"Bearer {stranger_tokens['access_token']}"}

    # Stranger (and anonymous) cannot run any stage of the pipeline for this citizen.
    assert (
        await client.post("/api/eligibility/evaluate", json={"citizen_id": citizen_id}, headers=stranger_headers)
    ).status_code == 403
    assert (
        await client.post("/api/eligibility/evaluate", json={"citizen_id": citizen_id})
    ).status_code == 403
    assert (
        await client.post("/api/conflicts/detect", json={"citizen_id": citizen_id}, headers=stranger_headers)
    ).status_code == 403
    assert (
        await client.post("/api/bundle/optimize", json={"citizen_id": citizen_id}, headers=stranger_headers)
    ).status_code == 403
    assert (
        await client.post("/api/agent/run", json={"citizen_id": citizen_id}, headers=stranger_headers)
    ).status_code == 403
    assert (
        await client.get(f"/api/agent/trace/{citizen_id}", headers=stranger_headers)
    ).status_code == 403

    # Owner can run the full pipeline.
    eval_res = await client.post(
        "/api/eligibility/evaluate", json={"citizen_id": citizen_id}, headers=owner_headers
    )
    assert eval_res.status_code == 200
    bundle_res = await client.post(
        "/api/bundle/optimize", json={"citizen_id": citizen_id}, headers=owner_headers
    )
    assert bundle_res.status_code == 200
    bundle_id = bundle_res.json()["bundle_id"]

    # Bundle/checklist ownership is enforced via the underlying citizen even though the
    # request only carries a bundle_id, not a citizen_id.
    assert (await client.get(f"/api/bundle/{bundle_id}", headers=stranger_headers)).status_code == 403
    assert (await client.get(f"/api/bundle/{bundle_id}", headers=owner_headers)).status_code == 200

    assert (
        await client.post("/api/checklist/generate", json={"bundle_id": bundle_id}, headers=stranger_headers)
    ).status_code == 403
    checklist_res = await client.post(
        "/api/checklist/generate", json={"bundle_id": bundle_id}, headers=owner_headers
    )
    assert checklist_res.status_code == 200
    assert (await client.get(f"/api/checklist/{bundle_id}", headers=stranger_headers)).status_code == 403
    assert (await client.get(f"/api/checklist/{bundle_id}", headers=owner_headers)).status_code == 200


async def test_admin_can_access_owned_citizen_pipeline(client, db):
    await seed_schemes_if_empty(db)
    owner_tokens = await _login(client, "pipeline_owner2@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_tokens['access_token']}"}
    citizen_id = await _make_owned_citizen(client, owner_headers)

    admin_tokens = await _login(client, "pipeline_admin@example.com", role="admin")
    admin_headers = {"Authorization": f"Bearer {admin_tokens['access_token']}"}

    assert (
        await client.post("/api/eligibility/evaluate", json={"citizen_id": citizen_id}, headers=admin_headers)
    ).status_code == 200
    assert (
        await client.get(f"/api/agent/trace/{citizen_id}", headers=admin_headers)
    ).status_code == 200
