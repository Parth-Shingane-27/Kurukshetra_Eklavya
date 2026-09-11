"""Rule Engine unit tests: operators, missing-field/indeterminate handling, AND/OR grouping.

Pure functions — no DB, no API — per Section 22's unit-test scope for the Rule Engine.
"""

from datetime import date

from app.modules.rule_engine.engine import build_profile_context, compute_age, evaluate_scheme


def _rule(field_name, operator, value, group="A"):
    return {"field_name": field_name, "operator": operator, "value": value, "logical_group": group}


def test_compute_age_before_and_after_birthday():
    assert compute_age(date(2000, 6, 15), as_of=date(2026, 6, 14)) == 25
    assert compute_age(date(2000, 6, 15), as_of=date(2026, 6, 15)) == 26


def test_build_profile_context_derives_age_from_string_dob():
    context = build_profile_context({"date_of_birth": "2000-01-01", "state": "Bihar"})
    assert context["age"] >= 25
    assert context["state"] == "Bihar"


def test_scheme_with_no_rules_is_eligible():
    outcome = evaluate_scheme({"rules": []}, {})
    assert outcome["status"] == "eligible"
    assert outcome["reasons"] == []


def test_operator_equals():
    scheme = {"rules": [_rule("occupation", "=", "farmer")]}
    assert evaluate_scheme(scheme, {"occupation": "farmer"})["status"] == "eligible"
    assert evaluate_scheme(scheme, {"occupation": "salaried"})["status"] == "not_eligible"


def test_operator_comparisons():
    scheme = {"rules": [_rule("land_holding_acres", "<=", 5)]}
    assert evaluate_scheme(scheme, {"land_holding_acres": 3})["status"] == "eligible"
    assert evaluate_scheme(scheme, {"land_holding_acres": 8})["status"] == "not_eligible"

    scheme_gt = {"rules": [_rule("age", ">", 18)]}
    assert evaluate_scheme(scheme_gt, {"age": 25})["status"] == "eligible"
    assert evaluate_scheme(scheme_gt, {"age": 18})["status"] == "not_eligible"

    scheme_gte = {"rules": [_rule("age", ">=", 18)]}
    assert evaluate_scheme(scheme_gte, {"age": 18})["status"] == "eligible"

    scheme_lt = {"rules": [_rule("age", "<", 35)]}
    assert evaluate_scheme(scheme_lt, {"age": 34})["status"] == "eligible"
    assert evaluate_scheme(scheme_lt, {"age": 35})["status"] == "not_eligible"


def test_operator_in():
    scheme = {"rules": [_rule("social_category", "in", ["SC", "ST"])]}
    assert evaluate_scheme(scheme, {"social_category": "SC"})["status"] == "eligible"
    assert evaluate_scheme(scheme, {"social_category": "General"})["status"] == "not_eligible"


def test_missing_field_is_indeterminate_not_silently_excluded_or_included():
    scheme = {"rules": [_rule("bpl_status", "=", True)]}
    outcome = evaluate_scheme(scheme, {"bpl_status": None})
    assert outcome["status"] == "indeterminate"
    assert outcome["reasons"][0]["field_name"] == "bpl_status"


def test_missing_field_absent_from_context_entirely_is_also_indeterminate():
    scheme = {"rules": [_rule("bpl_status", "=", True)]}
    outcome = evaluate_scheme(scheme, {})
    assert outcome["status"] == "indeterminate"


def test_false_is_a_real_value_not_missing():
    # disability_status explicitly False must NOT be treated as missing input.
    scheme = {"rules": [_rule("disability_status", "=", True)]}
    outcome = evaluate_scheme(scheme, {"disability_status": False})
    assert outcome["status"] == "not_eligible"


def test_and_within_group_first_failure_reported():
    scheme = {
        "rules": [
            _rule("occupation", "=", "farmer"),
            _rule("land_holding_acres", "<=", 5),
        ]
    }
    outcome = evaluate_scheme(scheme, {"occupation": "salaried", "land_holding_acres": 3})
    assert outcome["status"] == "not_eligible"
    assert outcome["reasons"][0]["field_name"] == "occupation"


def test_or_across_groups_eligible_via_second_group():
    scheme = {
        "rules": [
            _rule("social_category", "in", ["SC", "ST"], group="A"),
            _rule("bpl_status", "=", True, group="B"),
        ]
    }
    # Group A fails (General), but group B passes -> eligible overall.
    outcome = evaluate_scheme(scheme, {"social_category": "General", "bpl_status": True})
    assert outcome["status"] == "eligible"


def test_or_across_groups_indeterminate_beats_not_eligible():
    scheme = {
        "rules": [
            _rule("social_category", "in", ["SC", "ST"], group="A"),
            _rule("bpl_status", "=", True, group="B"),
        ]
    }
    # Group A is fully known and fails; group B is missing data. BR-002 priority:
    # eligible > indeterminate > not_eligible, since group B might still resolve to eligible.
    outcome = evaluate_scheme(scheme, {"social_category": "General", "bpl_status": None})
    assert outcome["status"] == "indeterminate"
    assert outcome["reasons"][0]["field_name"] == "bpl_status"
