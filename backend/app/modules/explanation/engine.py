"""Deterministic template explanation — BR-010's fallback, and Section 16's guarantee that
explanation text only restates already-computed structured facts (eligibility, conflicts,
optimization), never introduces a new eligibility claim of its own.
"""


def build_template_explanation(bundle_result: dict) -> str:
    included = bundle_result["included"]
    excluded = bundle_result["excluded"]

    if not included and not excluded:
        return "No schemes were found to be eligible based on the information provided."

    lines = []
    if included:
        names = ", ".join(s["scheme_name"] for s in included)
        lines.append(
            f"Based on your profile, you are eligible for {len(included)} scheme(s): {names}. "
            f"Together these provide an estimated total benefit of "
            f"{bundle_result['total_benefit_value']:,.0f}."
        )
        for s in included:
            lines.append(
                f"- {s['scheme_name']}: included because your profile satisfied all of its "
                f"eligibility conditions."
            )
    else:
        lines.append(
            "You were eligible for one or more schemes, but none could be included in a "
            "conflict-free bundle."
        )

    if excluded:
        lines.append("The following eligible scheme(s) were excluded from your bundle due to conflicts:")
        for e in excluded:
            lines.append(f"- {e['scheme_name']}: {e['reason']}")

    return "\n".join(lines)
