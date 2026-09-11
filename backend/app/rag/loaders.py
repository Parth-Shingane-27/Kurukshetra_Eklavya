"""Loads the raw scheme corpus (gov_schemes_cleaned.json, Section 1 of the brief) that backs
the RAG layer. Distinct from `database/seed_schemes.json`, which is the small, hand-curated,
structured set the deterministic Rule Engine evaluates — that file is untouched by this module.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ("scheme_id", "scheme_name")


def load_gov_schemes_corpus(path: str | Path) -> list[dict[str, Any]]:
    """Load and lightly validate the cleaned scheme corpus.

    Returns only records with a non-blank scheme_id/scheme_name (BR-style: never silently drop
    a record without accounting for it — a skip is logged with just the offending index, never
    the record content, since this is public scheme data but still shouldn't be dumped into logs
    wholesale).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Policy corpus not found at {path}. Run `python clean_gov_schemes.py` from the "
            "repo root first, or set POLICY_CORPUS_PATH to an existing file."
        )

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Expected a JSON list of scheme records in {path}, got {type(raw)}")

    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    skipped_missing_fields = 0
    skipped_duplicates = 0

    for idx, record in enumerate(raw):
        scheme_id = str(record.get("scheme_id") or "").strip()
        scheme_name = str(record.get("scheme_name") or "").strip()
        if not scheme_id or not scheme_name:
            skipped_missing_fields += 1
            logger.warning("Skipping corpus record at index %d: missing scheme_id/scheme_name", idx)
            continue
        if scheme_id in seen_ids:
            skipped_duplicates += 1
            continue
        seen_ids.add(scheme_id)
        records.append(record)

    logger.info(
        "Loaded %d corpus records from %s (skipped %d missing required fields, %d duplicates)",
        len(records), path, skipped_missing_fields, skipped_duplicates,
    )
    return records
