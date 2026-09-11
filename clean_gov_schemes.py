"""
Clean and preprocess gov_schemes.csv into a structured dataset describing
government schemes, their eligibility criteria, and required documents.

Usage: python clean_gov_schemes.py
Outputs:
  - gov_schemes_cleaned.csv   (flat, spreadsheet-friendly)
  - gov_schemes_cleaned.json  (nested, list fields expanded — for programmatic use)
"""
import json
import re
import unicodedata

import pandas as pd

SRC = "gov_schemes.csv"
OUT_CSV = "gov_schemes_cleaned.csv"
OUT_JSON = "gov_schemes_cleaned.json"

TEXT_COLUMNS = [
    "scheme_name", "slug", "details", "benefits", "eligibility",
    "application", "documents", "level", "scheme_category", "tags",
]

# Visually-identical Cyrillic homoglyphs occasionally substituted for Latin
# letters in a handful of scraped rows (e.g. "a??ly f?r ?nline" -> "apply for online").
HOMOGLYPHS = str.maketrans({
    "а": "a", "А": "A", "е": "e", "Е": "E", "о": "o", "О": "O",
    "р": "p", "Р": "P", "с": "c", "С": "C", "х": "x", "Х": "X",
    "у": "y", "У": "Y", "к": "k", "К": "K", "м": "m", "М": "M",
    "н": "H", "Н": "H", "т": "t", "Т": "T", "в": "B", "В": "B",
})

ZERO_WIDTH_RE = re.compile(r"[﻿​‌‍\xad]")
WS_RE = re.compile(r"\s+")


def normalize_text(value):
    if not isinstance(value, str):
        return value
    text = value.translate(HOMOGLYPHS)
    text = unicodedata.normalize("NFC", text)
    text = ZERO_WIDTH_RE.sub("", text)
    text = text.replace("\xa0", " ")
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-").replace("‐", "-")
    text = text.replace("•", " - ").replace("●", " - ")
    text = WS_RE.sub(" ", text).strip()
    return text


ACRONYM_DOT_RE1 = re.compile(r"\b([A-Z])\.(?=[A-Z]\.)")
ACRONYM_DOT_RE2 = re.compile(r"\b([A-Z])\.(?=[A-Z]\b)")
DOC_SPLIT_RE = re.compile(r"\.\s+(?=[A-Z0-9])")


def split_documents_best_effort(text):
    """Best-effort split of the free-text documents blob into a list.

    The source text is not consistently delimited (some rows use '. ' between
    items, many run items together with no punctuation at all), so this is a
    heuristic, not a reliable parse. Callers should treat `documents_list` as
    a lossy convenience view and `documents` (cleaned free text) as the
    source of truth.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    protected = ACRONYM_DOT_RE1.sub(r"\1<DOT>", text)
    protected = ACRONYM_DOT_RE2.sub(r"\1<DOT>", protected)
    parts = DOC_SPLIT_RE.split(protected)
    items = []
    for p in parts:
        p = p.replace("<DOT>", ".").strip().rstrip(".").strip()
        if p:
            items.append(p)
    return items


def split_csv_list(text):
    """Split on ', ' (comma+space), not bare ',' — some category/tag values
    contain an internal comma with no following space (e.g. the taxonomy
    entry "Agriculture,Rural & Environment" is one category, not two).
    """
    if not isinstance(text, str) or not text.strip():
        return []
    return [t.strip() for t in text.split(", ") if t.strip()]


def main():
    df = pd.read_csv(SRC, encoding="utf-8")

    # Drop the fully-empty stray column and rename to snake_case.
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")])
    df = df.rename(columns={"schemeCategory": "scheme_category"})

    before = len(df)
    df = df.drop_duplicates()
    dupes_dropped = before - len(df)

    # Normalize whitespace/encoding artifacts across every text field.
    for col in TEXT_COLUMNS:
        if col in df.columns:
            df[col] = df[col].map(normalize_text)

    # Missing free-text fields: represent as empty string, not NaN.
    for col in ["application", "documents", "tags"]:
        df[col] = df[col].fillna("")

    # Structured list views of the comma-delimited fields.
    df["scheme_category_list"] = df["scheme_category"].map(split_csv_list)
    df["tags_list"] = df["tags"].map(split_csv_list)

    # Best-effort structured view of the documents blob (see docstring above).
    df["documents_list"] = df["documents"].map(split_documents_best_effort)

    df = df.reset_index(drop=True)
    df.insert(0, "scheme_id", df.index + 1)

    df.to_csv(OUT_CSV, index=False, encoding="utf-8")

    records = df.to_dict(orient="records")
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Source rows: {before}")
    print(f"Exact duplicate rows dropped: {dupes_dropped}")
    print(f"Final scheme count: {len(df)}")
    print(f"Missing 'application': {(df['application'] == '').sum()}")
    print(f"Missing 'documents': {(df['documents'] == '').sum()}")
    print(f"Missing 'tags': {(df['tags'] == '').sum()}")
    print(f"Wrote {OUT_CSV} and {OUT_JSON}")


if __name__ == "__main__":
    main()
