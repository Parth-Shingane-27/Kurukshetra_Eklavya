"""Conflict Detection Engine (FR-005, BR-004, BR-005).

Pure functions over plain dicts — no DB access — so the module is trivially unit-testable
and reusable by both the /api/conflicts/detect endpoint and the Bundle Optimizer.
"""


def detect_conflicts(eligible_schemes: list[dict], conflict_rules: list[dict]) -> list[dict]:
    """
    eligible_schemes: scheme dicts with at least 'id', 'name', 'conflict_group'.
    conflict_rules: dicts with 'scheme_a_id', 'scheme_b_id', 'conflict_type', 'reason'
                     (ids as strings, matching scheme['id']).

    Returns a list of {scheme_a_id, scheme_a_name, scheme_b_id, scheme_b_name,
    conflict_type, reason} entries, each pair reported at most once.
    """
    eligible_ids = {s["id"] for s in eligible_schemes}
    id_to_scheme = {s["id"]: s for s in eligible_schemes}
    conflicts: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()

    def add_conflict(a_id: str, b_id: str, conflict_type: str, reason: str) -> None:
        key = tuple(sorted((a_id, b_id)))
        if key in seen_pairs:
            return
        seen_pairs.add(key)
        conflicts.append(
            {
                "scheme_a_id": key[0],
                "scheme_a_name": id_to_scheme[key[0]]["name"],
                "scheme_b_id": key[1],
                "scheme_b_name": id_to_scheme[key[1]]["name"],
                "conflict_type": conflict_type,
                "reason": reason,
            }
        )

    # BR-004: explicit pairwise declarations.
    for rule in conflict_rules:
        a_id, b_id = rule["scheme_a_id"], rule["scheme_b_id"]
        if a_id in eligible_ids and b_id in eligible_ids:
            add_conflict(
                a_id,
                b_id,
                rule["conflict_type"],
                rule.get("reason") or "Declared as mutually exclusive in the scheme knowledge base.",
            )

    # BR-005: shared conflict_group -> every pair within the group conflicts.
    groups: dict[str, list[str]] = {}
    for scheme in eligible_schemes:
        group = scheme.get("conflict_group")
        if group:
            groups.setdefault(group, []).append(scheme["id"])

    for group, ids in groups.items():
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                add_conflict(
                    ids[i],
                    ids[j],
                    "conflict_group",
                    f"Both belong to conflict group '{group}'; at most one may be selected.",
                )

    return conflicts
