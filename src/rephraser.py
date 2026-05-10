"""Rephrase scraped horoscope text using Claude Haiku (lightweight + fast).

Called after scraping to shorten and clean up the text before rendering.
Requires ANTHROPIC_API_KEY in the environment. If the key is missing or the
call fails, the original scraped text is returned unchanged.
"""
from __future__ import annotations

import logging

from . import config

log = logging.getLogger(__name__)

_PROMPT = (
    "You are a concise astrology writer. Rephrase the horoscope below into "
    "2-3 punchy sentences (80-120 words). Keep the spiritual/astrological tone, "
    "drop any repeated sentences, and avoid generic filler. "
    "Return only the rephrased text with no commentary or quotation marks.\n\n"
    "Horoscope:\n{text}"
)


def rephrase(text: str) -> str:
    """Return a shorter, rephrased version of *text* via Claude Haiku.

    Falls back to *text* unchanged if ANTHROPIC_API_KEY is unset or the call fails.
    """
    if not config.ANTHROPIC_API_KEY:
        log.debug("ANTHROPIC_API_KEY not set — skipping rephrase")
        return text

    try:
        import anthropic  # lazy import so the package is optional at import time

        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": _PROMPT.format(text=text)}],
        )
        rephrased = msg.content[0].text.strip()
        log.info("rephrased horoscope: %d → %d chars", len(text), len(rephrased))
        return rephrased
    except Exception as e:  # noqa: BLE001
        log.warning("rephrase failed (%s), using original text", e)
        return text
