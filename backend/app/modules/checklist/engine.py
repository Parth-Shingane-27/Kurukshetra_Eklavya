"""Document & Checklist Manager (FR-008, FR-009, BR-008, BR-009). Pure functions over
plain dicts — no DB access.
"""


def compute_missing_documents(bundle_schemes: list[dict], held_documents: set[str]) -> list[dict]:
    """BR-008: per bundle scheme, which required documents the citizen hasn't declared held."""
    results = []
    for scheme in bundle_schemes:
        missing = [
            req["document_type"]
            for req in scheme.get("document_requirements", [])
            if req["document_type"] not in held_documents
        ]
        results.append({"scheme_id": scheme["id"], "scheme_name": scheme["name"], "missing_documents": missing})
    return results


def build_checklist(bundle_schemes: list[dict], held_documents: set[str]) -> list[dict]:
    """BR-009: consolidate document requirements across bundle schemes — a document required
    by more than one scheme is listed once, annotated with every scheme that requires it.
    """
    by_doc: dict[str, dict] = {}
    for scheme in bundle_schemes:
        for req in scheme.get("document_requirements", []):
            doc_type = req["document_type"]
            entry = by_doc.setdefault(
                doc_type,
                {
                    "document_type": doc_type,
                    "related_scheme_ids": [],
                    "related_scheme_names": [],
                    "status": "held" if doc_type in held_documents else "missing",
                },
            )
            entry["related_scheme_ids"].append(scheme["id"])
            entry["related_scheme_names"].append(scheme["name"])

    items = list(by_doc.values())
    items.sort(key=lambda item: item["status"] != "missing")  # missing (actionable) items first
    return items
