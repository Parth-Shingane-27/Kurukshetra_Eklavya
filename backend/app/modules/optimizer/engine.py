"""Bundle Optimizer (FR-006, BR-006, BR-007).

Models eligible schemes as a conflict graph (edges from Conflict Detection Engine output)
and selects the maximum-weight independent set — the conflict-free subset maximizing total
benefit value. Solved exactly per connected component via bitmask brute force (components
are small: dozens of schemes per citizen at prototype scale per Section 23); a component
larger than EXACT_COMPONENT_LIMIT falls back to a greedy heuristic, per Section 18.

BR-007 tie-break (equal total benefit): prefer more distinct schemes, then the bundle whose
schemes were "added to the knowledge base most recently". Mongo ObjectIds are monotonically
increasing with insertion time, so a scheme's id string doubles as that recency signal —
avoiding a separate `created_at` lookup, which would tie for every scheme in one seed batch.
"""

EXACT_COMPONENT_LIMIT = 20


def _build_adjacency(scheme_ids: list[str], conflicts: list[dict]) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = {sid: set() for sid in scheme_ids}
    for c in conflicts:
        a_id, b_id = c["scheme_a_id"], c["scheme_b_id"]
        if a_id in adjacency and b_id in adjacency:
            adjacency[a_id].add(b_id)
            adjacency[b_id].add(a_id)
    return adjacency


def _connected_components(adjacency: dict[str, set[str]]) -> list[list[str]]:
    visited: set[str] = set()
    components: list[list[str]] = []
    for start in adjacency:
        if start in visited:
            continue
        visited.add(start)
        stack = [start]
        component = []
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in adjacency[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        components.append(component)
    return components


def _best_independent_subset(
    component: list[str], adjacency: dict[str, set[str]], weight: dict[str, float]
) -> list[str]:
    if len(component) <= EXACT_COMPONENT_LIMIT:
        best_subset: tuple[str, ...] = ()
        best_key = (0.0, 0, "", ())
        n = len(component)
        for mask in range(1 << n):
            subset = tuple(component[i] for i in range(n) if mask & (1 << i))
            subset_set = set(subset)
            if any(adjacency[s] & subset_set for s in subset):
                continue  # not independent — some pair in this subset conflicts
            total = sum(weight[s] for s in subset)
            key = (total, len(subset), max(subset) if subset else "", tuple(sorted(subset)))
            if key > best_key:
                best_key = key
                best_subset = subset
        return list(best_subset)

    # Greedy fallback for large components: highest-benefit-first, skip on conflict.
    selected: list[str] = []
    selected_set: set[str] = set()
    for sid in sorted(component, key=lambda s: (-weight[s], s)):
        if not (adjacency[sid] & selected_set):
            selected.append(sid)
            selected_set.add(sid)
    return selected


def optimize_bundle(eligible_schemes: list[dict], conflicts: list[dict]) -> dict:
    """
    eligible_schemes: scheme dicts with 'id', 'name', 'benefit_value_estimate'.
    conflicts: output of conflict_engine.engine.detect_conflicts().

    Returns {"scheme_ids": [...], "total_benefit_value": float,
             "excluded": [{"scheme_id", "scheme_name", "reason"}, ...]}.
    """
    scheme_ids = [s["id"] for s in eligible_schemes]
    weight = {s["id"]: s["benefit_value_estimate"] for s in eligible_schemes}
    id_to_scheme = {s["id"]: s for s in eligible_schemes}

    adjacency = _build_adjacency(scheme_ids, conflicts)
    components = _connected_components(adjacency)

    selected: list[str] = []
    for component in components:
        selected.extend(_best_independent_subset(component, adjacency, weight))
    selected_set = set(selected)

    conflict_by_pair: dict[tuple[str, str], dict] = {}
    for c in conflicts:
        conflict_by_pair[(c["scheme_a_id"], c["scheme_b_id"])] = c
        conflict_by_pair[(c["scheme_b_id"], c["scheme_a_id"])] = c

    excluded = []
    for sid in scheme_ids:
        if sid in selected_set:
            continue
        conflicting_selected = sorted(adjacency[sid] & selected_set)
        if conflicting_selected:
            parts = []
            for other in conflicting_selected:
                other_name = id_to_scheme[other]["name"]
                conflict_type = conflict_by_pair[(sid, other)]["conflict_type"]
                if conflict_type == "conflict_group":
                    parts.append(f"same conflict group as '{other_name}'")
                else:
                    parts.append(f"mutually exclusive with '{other_name}'")
            reason = f"Excluded: {', '.join(parts)}."
        else:
            # Not expected for positive benefit values (an unconflicted scheme is always
            # included), but kept as a defensive fallback message.
            reason = "Excluded by the optimizer in favor of a higher-value combination."
        excluded.append({"scheme_id": sid, "scheme_name": id_to_scheme[sid]["name"], "reason": reason})

    return {
        "scheme_ids": selected,
        "total_benefit_value": sum(weight[s] for s in selected),
        "excluded": excluded,
    }
