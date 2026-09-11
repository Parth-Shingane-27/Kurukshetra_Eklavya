"""Document & Checklist Manager unit tests (BR-008, BR-009; TC-018–020)."""

from app.modules.checklist.engine import build_checklist, compute_missing_documents


def _scheme(id_, name, doc_types):
    return {
        "id": id_,
        "name": name,
        "document_requirements": [{"document_type": d, "is_mandatory": True} for d in doc_types],
    }


def test_missing_documents_when_citizen_holds_none():
    schemes = [_scheme("s1", "A", ["Aadhaar Card", "Ration Card"])]
    result = compute_missing_documents(schemes, held_documents=set())
    assert result == [{"scheme_id": "s1", "scheme_name": "A", "missing_documents": ["Aadhaar Card", "Ration Card"]}]


def test_no_missing_documents_when_all_held():
    schemes = [_scheme("s1", "A", ["Aadhaar Card"])]
    result = compute_missing_documents(schemes, held_documents={"Aadhaar Card"})
    assert result[0]["missing_documents"] == []


def test_partial_holding():
    schemes = [_scheme("s1", "A", ["Aadhaar Card", "Ration Card", "Income Certificate"])]
    result = compute_missing_documents(schemes, held_documents={"Aadhaar Card"})
    assert result[0]["missing_documents"] == ["Ration Card", "Income Certificate"]


def test_checklist_deduplicates_shared_document_across_schemes():
    schemes = [
        _scheme("s1", "PM-KISAN", ["Aadhaar Card", "Bank Passbook"]),
        _scheme("s2", "Old Age Pension", ["Aadhaar Card", "BPL Ration Card"]),
    ]
    items = build_checklist(schemes, held_documents=set())
    aadhaar = next(i for i in items if i["document_type"] == "Aadhaar Card")
    assert set(aadhaar["related_scheme_ids"]) == {"s1", "s2"}
    assert set(aadhaar["related_scheme_names"]) == {"PM-KISAN", "Old Age Pension"}
    assert len(items) == 3  # Aadhaar Card, Bank Passbook, BPL Ration Card


def test_checklist_status_held_vs_missing():
    schemes = [_scheme("s1", "A", ["Aadhaar Card", "Bank Passbook"])]
    items = build_checklist(schemes, held_documents={"Aadhaar Card"})
    by_type = {i["document_type"]: i["status"] for i in items}
    assert by_type["Aadhaar Card"] == "held"
    assert by_type["Bank Passbook"] == "missing"


def test_checklist_missing_items_sorted_first():
    schemes = [_scheme("s1", "A", ["Held Doc", "Missing Doc"])]
    items = build_checklist(schemes, held_documents={"Held Doc"})
    assert [i["status"] for i in items] == ["missing", "held"]
