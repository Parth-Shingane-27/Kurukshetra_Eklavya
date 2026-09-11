"""Deterministic eligibility rule evaluation (FR-004, BR-001, BR-002, Section 29's
logical_group AND/OR support).

Rules sharing the same `logical_group` are AND-ed together; a scheme is eligible if
ANY group's rules all pass (OR across groups). A group whose fields are not all
present in the profile cannot be evaluated at all and is treated as missing data,
not as a failure — see BR-002's stated priority: eligible > indeterminate > not_eligible.
"""

from datetime import date, datetime
from typing import Any

_OPERATORS = {"=", "<", "<=", ">", ">=", "in"}


def compute_age(date_of_birth: date, as_of: date | None = None) -> int:
    as_of = as_of or date.today()
    had_birthday = (as_of.month, as_of.day) >= (date_of_birth.month, date_of_birth.day)
    return as_of.year - date_of_birth.year - (0 if had_birthday else 1)


def build_profile_context(citizen: dict) -> dict:
    """Citizen profile fields plus derived fields (currently: `age` from `date_of_birth`)."""
    context = dict(citizen)
    dob = citizen.get("date_of_birth")
    if isinstance(dob, str):
        dob = date.fromisoformat(dob)
    elif isinstance(dob, datetime):
        dob = dob.date()
    if isinstance(dob, date):
        context["age"] = compute_age(dob)
    return context


def evaluate_condition(operator: str, actual: Any, expected: Any) -> bool:
    if operator == "=":
        return actual == expected
    if operator == "<":
        return actual < expected
    if operator == "<=":
        return actual <= expected
    if operator == ">":
        return actual > expected
    if operator == ">=":
        return actual >= expected
    if operator == "in":
        return actual in expected
    raise ValueError(f"Unsupported rule operator: {operator!r}")


def _describe(rule: dict, actual: Any, passed: bool) -> dict:
    return {
        "field_name": rule["field_name"],
        "message": (
            f"Requires {rule['field_name']} {rule['operator']} {rule['value']!r}; "
            f"profile has {actual!r} - {'matched' if passed else 'did not match'}."
        ),
    }


def evaluate_scheme(scheme: dict, profile_context: dict) -> dict:
    """Returns {"status": "eligible"|"not_eligible"|"indeterminate", "reasons": [...]}."""
    rules: list[dict] = scheme.get("rules", [])
    if not rules:
        return {"status": "eligible", "reasons": []}

    groups: dict[str | None, list[dict]] = {}
    for rule in rules:
        groups.setdefault(rule.get("logical_group"), []).append(rule)

    missing_fields: dict[str, None] = {}
    first_failure_reason: dict | None = None

    for group_rules in groups.values():
        missing_in_group = [
            r["field_name"] for r in group_rules if profile_context.get(r["field_name"]) is None
        ]
        if missing_in_group:
            for field_name in missing_in_group:
                missing_fields.setdefault(field_name, None)
            continue

        group_reasons = []
        group_passed = True
        for rule in group_rules:
            actual = profile_context.get(rule["field_name"])
            passed = evaluate_condition(rule["operator"], actual, rule["value"])
            reason = _describe(rule, actual, passed)
            group_reasons.append(reason)
            if not passed:
                group_passed = False
                if first_failure_reason is None:
                    first_failure_reason = reason
                break

        if group_passed:
            return {"status": "eligible", "reasons": group_reasons}

    if missing_fields:
        reasons = [
            {
                "field_name": field_name,
                "message": f"Required field '{field_name}' is missing from the citizen profile.",
            }
            for field_name in missing_fields
        ]
        return {"status": "indeterminate", "reasons": reasons}

    return {"status": "not_eligible", "reasons": [first_failure_reason]}
