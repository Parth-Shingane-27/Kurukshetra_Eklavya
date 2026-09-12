"""A-011 — Maharashtra/MahaDBT representative seed set: a second, distinct seed file loaded
into the same `schemes` collection via an explicit, idempotent loader (not the startup
seeder)."""

import json
from pathlib import Path

from app.models.scheme import SchemeCreate
from app.modules.scheme_kb.service import seed_maharashtra_schemes, seed_schemes_if_empty

MAHARASHTRA_SEED_FILE = (
    Path(__file__).resolve().parents[2] / "database" / "seed_schemes_maharashtra.json"
)


def test_every_maharashtra_scheme_parses_as_a_valid_scheme():
    """Catches a hand-authored rule/value shape mistake at test time, not first-run-in-prod
    time — mirrors how FR-011's SchemeCreate validation already guards admin-entered schemes."""
    data = json.loads(MAHARASHTRA_SEED_FILE.read_text(encoding="utf-8"))
    assert len(data["schemes"]) == 5
    for scheme in data["schemes"]:
        payload = {k: v for k, v in scheme.items() if k != "seed_key"}
        SchemeCreate(**payload)  # raises if any rule/operator/value shape is invalid


def test_maharashtra_schemes_do_not_duplicate_pm_kisan(db):
    """A-011: PM-KISAN is deliberately not repeated in the Maharashtra file, since it already
    exists in seed_schemes.json — verifies that decision holds, not just the doc comment."""
    data = json.loads(MAHARASHTRA_SEED_FILE.read_text(encoding="utf-8"))
    names = {s["name"] for s in data["schemes"]}
    assert not any("PM-KISAN" in name for name in names)


async def test_seed_maharashtra_schemes_inserts_all_five(db):
    result = await seed_maharashtra_schemes(db)
    assert len(result["inserted"]) == 5
    assert result["skipped"] == []
    assert await db.schemes.count_documents({}) == 5


async def test_seed_maharashtra_schemes_is_idempotent(db):
    first = await seed_maharashtra_schemes(db)
    assert len(first["inserted"]) == 5

    second = await seed_maharashtra_schemes(db)
    assert second["inserted"] == []
    assert len(second["skipped"]) == 5
    assert await db.schemes.count_documents({}) == 5


async def test_maharashtra_set_coexists_with_original_seed_set(db):
    await seed_schemes_if_empty(db)
    result = await seed_maharashtra_schemes(db)
    assert len(result["inserted"]) == 5
    assert await db.schemes.count_documents({}) == 8 + 5


async def test_ramai_awas_conflicts_with_pmay_via_shared_conflict_group(client, db):
    """BR-005: conflict_group is just a shared string, not scoped to one seed file — a citizen
    eligible for both Ramai Awas Gharkul (Maharashtra file) and PMAY-Rural (original file)
    must still have the conflict detected and the bundle resolved, proving the two files'
    conflict_group values genuinely interact once loaded into the same collection."""
    await seed_schemes_if_empty(db)
    await seed_maharashtra_schemes(db)

    citizen_res = await client.post(
        "/api/citizens",
        json={
            "name": "Cross-File Conflict Test",
            "date_of_birth": "1980-01-01",
            "state": "Maharashtra",
            "district": "Pune",
            "bpl_status": True,
            "annual_income": 200000,
            "social_category": "SC",
        },
    )
    citizen_id = citizen_res.json()["id"]

    eval_res = await client.post("/api/eligibility/evaluate", json={"citizen_id": citizen_id})
    assert eval_res.status_code == 200
    eligible_names = {r["scheme_name"] for r in eval_res.json()["results"] if r["status"] == "eligible"}
    assert "Pradhan Mantri Awas Yojana (Rural)" in eligible_names
    assert "Ramai Awas Gharkul Yojana" in eligible_names

    conflicts_res = await client.post("/api/conflicts/detect", json={"citizen_id": citizen_id})
    assert conflicts_res.status_code == 200
    conflict_pairs = {
        frozenset((c["scheme_a_name"], c["scheme_b_name"])) for c in conflicts_res.json()["conflicts"]
    }
    assert frozenset(("Pradhan Mantri Awas Yojana (Rural)", "Ramai Awas Gharkul Yojana")) in conflict_pairs

    bundle_res = await client.post("/api/bundle/optimize", json={"citizen_id": citizen_id})
    assert bundle_res.status_code == 200
    included_names = {e for e in bundle_res.json()["scheme_ids"]}
    # Exactly one of the two conflicting housing schemes survives into the optimized bundle.
    housing_scheme_ids = set()
    for r in eval_res.json()["results"]:
        if r["scheme_name"] in ("Pradhan Mantri Awas Yojana (Rural)", "Ramai Awas Gharkul Yojana"):
            housing_scheme_ids.add(r["scheme_id"])
    assert len(included_names & housing_scheme_ids) == 1
