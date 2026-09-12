"""CLI entry point for loading the Maharashtra/MahaDBT-aligned representative scheme set
(A-011, plan.md Section 4/13a) into the same `schemes` collection the app already uses.

Deliberately a separate, explicit script rather than something `seed_schemes_if_empty` runs
automatically — this augments an existing catalogue (real or demo), so an operator should
choose when to add it, not have it silently appear on every fresh backend startup.

Usage (from repo root):
    source backend/.venv/bin/activate   # or the Windows equivalent
    python backend/scripts/seed_maharashtra.py

Safe to re-run: each scheme is inserted only if no scheme with that exact name already exists.
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on sys.path

from app.core.config import get_settings  # noqa: E402
from app.core.db import get_client  # noqa: E402
from app.modules.scheme_kb.service import seed_maharashtra_schemes  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("seed_maharashtra")


async def main() -> None:
    settings = get_settings()
    db = get_client()[settings.mongo_db_name]

    result = await seed_maharashtra_schemes(db)

    if result["inserted"]:
        logger.info("Inserted %d scheme(s): %s", len(result["inserted"]), ", ".join(result["inserted"]))
    if result["skipped"]:
        logger.info(
            "Skipped %d scheme(s) already present: %s", len(result["skipped"]), ", ".join(result["skipped"])
        )
    if not result["inserted"] and not result["skipped"]:
        logger.warning("No schemes found in the Maharashtra seed file.")


if __name__ == "__main__":
    asyncio.run(main())
