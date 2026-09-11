"""RAG ingestion pipeline tests (Section 13 of the brief): dataset loading, required-field
validation, duplicate handling, chunking boundaries, metadata/source-label preservation.
Uses a small fixture corpus, never the full 3,397-scheme gov_schemes_cleaned.json.
"""

import json

import pytest

from app.rag.chunking import chunk_corpus, chunk_scheme_record
from app.rag.loaders import load_gov_schemes_corpus

FIXTURE_RECORDS = [
    {
        "scheme_id": 1,
        "scheme_name": "Sample Farmer Support Scheme",
        "details": "A scheme supporting small farmers.",
        "eligibility": "Applicant must be a farmer with less than 5 acres of land.",
        "benefits": "Cash transfer of Rs 6000 per year.",
        "application": "Apply online within 30 days of the notification.",
        "documents": "Aadhaar Card. Land Record.",
        "level": "Central",
        "scheme_category": "Agriculture",
        "scheme_category_list": ["Agriculture"],
    },
    {
        "scheme_id": 2,
        "scheme_name": "Duplicate Id Scheme",
        "details": "",
        "eligibility": "",
        "benefits": "",
        "application": "",
        "documents": "",
        "level": "State",
    },
    # Duplicate scheme_id (should be dropped by the loader).
    {"scheme_id": 2, "scheme_name": "Should Be Dropped As Duplicate"},
    # Missing scheme_name (should be dropped by the loader).
    {"scheme_id": 3, "scheme_name": "", "details": "orphan record"},
]


@pytest.fixture
def fixture_corpus_path(tmp_path):
    path = tmp_path / "fixture_corpus.json"
    path.write_text(json.dumps(FIXTURE_RECORDS), encoding="utf-8")
    return path


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_gov_schemes_corpus(tmp_path / "does_not_exist.json")


def test_load_rejects_non_list(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"not": "a list"}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_gov_schemes_corpus(path)


def test_load_drops_duplicates_and_missing_required_fields(fixture_corpus_path):
    records = load_gov_schemes_corpus(fixture_corpus_path)
    ids = [r["scheme_id"] for r in records]
    assert ids == [1, 2]  # duplicate scheme_id=2 and blank-name scheme_id=3 both dropped


def test_load_preserves_all_fields(fixture_corpus_path):
    records = load_gov_schemes_corpus(fixture_corpus_path)
    farmer = next(r for r in records if r["scheme_id"] == 1)
    assert farmer["benefits"] == "Cash transfer of Rs 6000 per year."
    assert farmer["scheme_category_list"] == ["Agriculture"]


def test_chunk_scheme_record_one_chunk_per_nonempty_section():
    chunks = chunk_scheme_record(FIXTURE_RECORDS[0])
    sections = {c.metadata.section for c in chunks}
    assert sections == {"details", "eligibility", "benefits", "application", "documents"}
    assert len(chunks) == 5


def test_chunk_scheme_record_skips_empty_sections():
    chunks = chunk_scheme_record(FIXTURE_RECORDS[1])  # all section fields blank
    assert chunks == []


def test_chunk_metadata_is_honestly_labeled_dataset_provided():
    chunks = chunk_scheme_record(FIXTURE_RECORDS[0])
    for chunk in chunks:
        assert chunk.metadata.source == "dataset_provided"
        assert chunk.metadata.source_url is None  # never fabricate an official URL
        assert chunk.metadata.scheme_id == "1"
        assert chunk.metadata.scheme_name == "Sample Farmer Support Scheme"


def test_chunk_id_is_deterministic_and_scoped_to_scheme_and_section():
    chunks = chunk_scheme_record(FIXTURE_RECORDS[0])
    eligibility_chunk = next(c for c in chunks if c.metadata.section == "eligibility")
    assert eligibility_chunk.chunk_id == "1::eligibility"


def test_chunk_corpus_aggregates_across_records(fixture_corpus_path):
    records = load_gov_schemes_corpus(fixture_corpus_path)
    chunks = chunk_corpus(records)
    assert len(chunks) == 5  # only scheme 1 has non-empty sections
    assert all(c.metadata.scheme_id == "1" for c in chunks)
