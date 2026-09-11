"""Conflict Detection Engine unit tests (BR-004, BR-005; TC-010–012)."""

from app.modules.conflict_engine.engine import detect_conflicts


def _scheme(id_, name, conflict_group=None):
    return {"id": id_, "name": name, "conflict_group": conflict_group}


def test_no_conflicts_is_a_valid_empty_result():
    schemes = [_scheme("s1", "A"), _scheme("s2", "B")]
    assert detect_conflicts(schemes, []) == []


def test_pairwise_conflict_rule_detected():
    schemes = [_scheme("s1", "Unemployment Allowance"), _scheme("s2", "Skill Stipend")]
    rules = [
        {
            "scheme_a_id": "s1",
            "scheme_b_id": "s2",
            "conflict_type": "mutually_exclusive",
            "reason": "budget-linked alternatives",
        }
    ]
    conflicts = detect_conflicts(schemes, rules)
    assert len(conflicts) == 1
    assert conflicts[0]["conflict_type"] == "mutually_exclusive"
    assert {conflicts[0]["scheme_a_id"], conflicts[0]["scheme_b_id"]} == {"s1", "s2"}


def test_pairwise_rule_ignored_if_one_side_not_eligible():
    schemes = [_scheme("s1", "Unemployment Allowance")]  # s2 not in the eligible set
    rules = [{"scheme_a_id": "s1", "scheme_b_id": "s2", "conflict_type": "mutually_exclusive"}]
    assert detect_conflicts(schemes, rules) == []


def test_conflict_group_detected_pairwise():
    schemes = [
        _scheme("s1", "PMAY", conflict_group="housing_subsidy"),
        _scheme("s2", "State Housing", conflict_group="housing_subsidy"),
    ]
    conflicts = detect_conflicts(schemes, [])
    assert len(conflicts) == 1
    assert conflicts[0]["conflict_type"] == "conflict_group"


def test_conflict_group_of_three_produces_three_pairs():
    schemes = [_scheme(f"s{i}", f"Scheme {i}", conflict_group="g") for i in range(3)]
    conflicts = detect_conflicts(schemes, [])
    assert len(conflicts) == 3  # C(3,2)


def test_different_conflict_groups_do_not_conflict():
    schemes = [
        _scheme("s1", "A", conflict_group="group1"),
        _scheme("s2", "B", conflict_group="group2"),
    ]
    assert detect_conflicts(schemes, []) == []


def test_duplicate_pair_reported_once():
    # Both a conflict_rules entry and coincidentally the same conflict_group.
    schemes = [
        _scheme("s1", "A", conflict_group="g"),
        _scheme("s2", "B", conflict_group="g"),
    ]
    rules = [{"scheme_a_id": "s1", "scheme_b_id": "s2", "conflict_type": "mutually_exclusive"}]
    conflicts = detect_conflicts(schemes, rules)
    assert len(conflicts) == 1
    assert conflicts[0]["conflict_type"] == "mutually_exclusive"  # first-seen wins
