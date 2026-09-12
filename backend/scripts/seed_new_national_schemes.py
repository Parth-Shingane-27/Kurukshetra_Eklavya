"""CLI entry point for loading any scheme in `database/seed_schemes.json` that isn't yet
present in the `schemes` collection (matched by exact `name`).

`seed_schemes_if_empty` (run automatically on backend startup) only bootstraps an EMPTY
collection — once the demo/Maharashtra schemes exist, newly-added entries in
`seed_schemes.json` (e.g. the national schemes appended after the original 8) are silently
never inserted. This script closes that gap the same way `seed_maharashtra.py` does for the
Maharashtra set: idempotent per-scheme by name, safe to re-run at any time.

Usage (from repo root):
    backend/.venv/Scripts/python backend/scripts/seed_new_national_schemes.py
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on sys.path

from app.core.config import get_settings  # noqa: E402
from app.core.db import get_client  # noqa: E402

SEED_FILE = Path(__file__).resolve().parents[2] / "database" / "seed_schemes.json"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("seed_new_national_schemes")


async def main() -> None:
    settings = get_settings()
    db = get_client()[settings.mongo_db_name]

    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)

    inserted: list[str] = []
    skipped: list[str] = []
    for scheme in data["schemes"]:
        scheme = dict(scheme)
        scheme.pop("seed_key", None)
        existing = await db.schemes.find_one({"name": scheme["name"]})
        if existing is not None:
            skipped.append(scheme["name"])
            continue
        doc = {**scheme, "created_at": now, "updated_at": now}
        await db.schemes.insert_one(doc)
        inserted.append(scheme["name"])

    if inserted:
        logger.info("Inserted %d scheme(s): %s", len(inserted), ", ".join(inserted))
    if skipped:
        logger.info("Skipped %d scheme(s) already present: %s", len(skipped), ", ".join(skipped))
    if not inserted and not skipped:
        logger.warning("No schemes found in the seed file.")


if __name__ == "__main__":
    asyncio.run(main())
