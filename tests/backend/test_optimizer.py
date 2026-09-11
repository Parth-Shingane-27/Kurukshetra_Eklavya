"""Bundle Optimizer unit tests (BR-006 max-weight independent set, BR-007 tie-break; TC-013–015)."""

from app.modules.conflict_engine.engine import detect_conflicts
from app.modules.optimizer.engine import optimize_bundle


def _scheme(id_, name, value, conflict_group=None):
    return {"id": id_, "name": name, "benefit_value_estimate": value, "conflict_group": conflict_group}


def test_no_conflicts_selects_everything():
    schemes = [_scheme("s1", "A", 100), _scheme("s2", "B", 200), _scheme("s3", "C", 50)]
    result = optimize_bundle(schemes, [])
    assert set(result["scheme_ids"]) == {"s1", "s2", "s3"}
    assert result["total_benefit_value"] == 350
    assert result["excluded"] == []


def test_empty_eligible_set_is_empty_bundle_not_an_error():
    result = optimize_bundle([], [])
    assert result == {"scheme_ids": [], "total_benefit_value": 0, "excluded": []}


def test_mutually_exclusive_pair_picks_higher_value():
    schemes = [_scheme("s1", "Cheap", 100), _scheme("s2", "Expensive", 200)]
    conflicts = [
        {"scheme_a_id": "s1", "scheme_b_id": "s2", "conflict_type": "mutually_exclusive", "reason": "x"}
    ]
    result = optimize_bundle(schemes, conflicts)
    assert result["scheme_ids"] == ["s2"]
    assert result["total_benefit_value"] == 200
    assert result["excluded"][0]["scheme_id"] == "s1"
    assert "Expensive" in result["excluded"][0]["reason"]


def test_conflict_group_picks_higher_value_and_names_the_winner():
    schemes = [
        _scheme("s1", "PMAY", 130000, conflict_group="housing_subsidy"),
        _scheme("s2", "State Housing", 100000, conflict_group="housing_subsidy"),
    ]
    conflicts = detect_conflicts(schemes, [])
    result = optimize_bundle(schemes, conflicts)
    assert result["scheme_ids"] == ["s1"]
    assert result["excluded"][0]["scheme_id"] == "s2"
    assert "PMAY" in result["excluded"][0]["reason"]
    assert "conflict group" in result["excluded"][0]["reason"]


def test_independent_set_beats_single_hub_node():
    # Path graph: B conflicts with both A and C; A and C don't conflict with each other.
    # {A, C} (30+40=70) beats {B} (50) alone -- a real max-weight independent set, not
    # just pairwise greedy exclusion.
    schemes = [_scheme("A", "A", 30), _scheme("B", "B", 50), _scheme("C", "C", 40)]
    conflicts = [
        {"scheme_a_id": "A", "scheme_b_id": "B", "conflict_type": "mutually_exclusive"},
        {"scheme_a_id": "B", "scheme_b_id": "C", "conflict_type": "mutually_exclusive"},
    ]
    result = optimize_bundle(schemes, conflicts)
    assert set(result["scheme_ids"]) == {"A", "C"}
    assert result["total_benefit_value"] == 70


def test_tie_break_prefers_more_schemes_when_total_value_equal():
    # {s1,s2} totals 100 with 2 schemes; {s3} alone totals 100 with 1 scheme.
    # s1/s2 conflict with s3 but not with each other.
    schemes = [
        _scheme("s1", "A", 40),
        _scheme("s2", "B", 60),
        _scheme("s3", "C", 100),
    ]
    conflicts = [
        {"scheme_a_id": "s1", "scheme_b_id": "s3", "conflict_type": "mutually_exclusive"},
        {"scheme_a_id": "s2", "scheme_b_id": "s3", "conflict_type": "mutually_exclusive"},
    ]
    result = optimize_bundle(schemes, conflicts)
    assert set(result["scheme_ids"]) == {"s1", "s2"}  # BR-007: more distinct schemes wins the tie


def test_tie_break_is_deterministic_across_repeated_runs():
    schemes = [_scheme("scheme-aaa", "A", 100), _scheme("scheme-bbb", "B", 100)]
    conflicts = [
        {"scheme_a_id": "scheme-aaa", "scheme_b_id": "scheme-bbb", "conflict_type": "mutually_exclusive"}
    ]
    results = {tuple(optimize_bundle(schemes, conflicts)["scheme_ids"]) for _ in range(10)}
    assert len(results) == 1  # always the same winner
