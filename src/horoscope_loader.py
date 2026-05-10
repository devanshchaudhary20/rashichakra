"""Fetches today's horoscope for each zodiac sign by scraping ganeshaspeaks.

If any sign fails, raises SkipDay so the caller can skip the day's post entirely.
"""
from __future__ import annotations

import json
import logging

from . import config, rephraser, scraper

log = logging.getLogger(__name__)


class SkipDay(Exception):
    """Raised when scraping fails and we should skip today's post."""


def load_zodiacs() -> list[dict]:
    with config.ZODIACS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def horoscope_all() -> list[dict]:
    """Fetch horoscopes for all 12 signs. Raises SkipDay if any fails."""
    zodiacs = load_zodiacs()
    out: list[dict] = []
    failures: list[tuple[str, str]] = []
    for z in zodiacs:
        try:
            text = scraper.fetch_horoscope(z["ganeshaspeaks_path"])
            text = rephraser.rephrase(text)
            out.append({**z, "horoscope": text})
            log.info("scraped %s OK (%d chars)", z["slug"], len(text))
        except Exception as e:  # noqa: BLE001
            failures.append((z["slug"], str(e)))
            log.error("scrape failed for %s: %s", z["slug"], e)

    if failures:
        msg = "; ".join(f"{slug}: {err}" for slug, err in failures)
        raise SkipDay(f"scrape failures ({len(failures)}/12): {msg}")
    return out
