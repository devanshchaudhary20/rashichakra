"""Scrape daily horoscope text from ganeshaspeaks.com."""
from __future__ import annotations

import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.ganeshaspeaks.com/"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class ScrapeError(Exception):
    pass


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _dedup_sentences(text: str) -> str:
    """Remove duplicate sentences while preserving order."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    seen: set[str] = set()
    unique: list[str] = []
    for s in sentences:
        key = s.strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(s.strip())
    return " ".join(unique)


def fetch_horoscope(zodiac_path: str, timeout: int = 20) -> str:
    """Fetch and parse the daily horoscope for one sign.

    Raises ScrapeError on any failure (HTTP, parsing, empty content).
    """
    url = BASE_URL + zodiac_path.lstrip("/")
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
    except requests.RequestException as e:
        raise ScrapeError(f"network error for {url}: {e}") from e

    if resp.status_code != 200:
        raise ScrapeError(f"HTTP {resp.status_code} for {url}")

    soup = BeautifulSoup(resp.text, "html.parser")

    # ganeshaspeaks marks the daily horoscope text inside a div with
    # class containing "today-horoscope" or similar; selectors change
    # occasionally, so we try a few in fallback order.
    candidates = [
        ("div", {"class": re.compile(r"today.*horoscope", re.I)}),
        ("div", {"class": re.compile(r"horoscope.*content", re.I)}),
        ("div", {"id": re.compile(r"daily", re.I)}),
        ("section", {"class": re.compile(r"daily", re.I)}),
    ]
    for tag, attrs in candidates:
        node = soup.find(tag, attrs=attrs)
        if node:
            text = _extract_paragraphs(node)
            if text:
                return text

    # Last-resort: grab the longest <p> tag in the document body.
    paragraphs = soup.find_all("p")
    if paragraphs:
        longest = max(paragraphs, key=lambda p: len(p.get_text(strip=True)))
        text = _dedup_sentences(_clean(longest.get_text(" ", strip=True)))
        if len(text) > 50:
            return text

    raise ScrapeError(f"could not locate horoscope text on {url}")


def _extract_paragraphs(node) -> Optional[str]:
    paragraphs = node.find_all("p")
    chunks: list[str] = []
    for p in paragraphs:
        t = _clean(p.get_text(" ", strip=True))
        if t and len(t) > 30:
            chunks.append(t)
    if not chunks:
        text = _dedup_sentences(_clean(node.get_text(" ", strip=True)))
        if len(text) > 50:
            return text
        return None
    full = _dedup_sentences(" ".join(chunks))
    return full
