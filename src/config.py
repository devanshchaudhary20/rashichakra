"""Centralized configuration."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


# --- Paths ---------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
ZODIACS_FILE = DATA_DIR / "zodiacs.json"
ZODIAC_IMAGES_DIR = DATA_DIR / "zodiac_images"
FONTS_DIR = ROOT / "fonts"
STATE_DIR = ROOT / "state"
POSTS_DIR = ROOT / "posts"

# Optional basename under ZODIAC_IMAGES_DIR for the date cover slide (e.g. cover.png).
# If empty, we try cover.jpg → cover.jpeg → cover.png in that folder.
COVER_IMAGE = os.getenv("COVER_IMAGE", "").strip()


# --- Fonts ---------------------------------------------------------------
FONT_BODY_REGULAR = FONTS_DIR / "Inter-Regular.ttf"
FONT_BODY_BOLD = FONTS_DIR / "Inter-Bold.ttf"
FONT_DISPLAY = FONTS_DIR / "PlayfairDisplay-Bold.ttf"


# --- Image render settings ----------------------------------------------
IMG_WIDTH = 1080
IMG_HEIGHT = 1350
HOROSCOPE_FONT_SIZE = 36
SIGN_NAME_FONT_SIZE = 64
DATE_FONT_SIZE = 56
HANDLE_FONT_SIZE = 26

TEXT_COLOR = (0, 0, 0)
DATE_COLOR = (0, 0, 0)
SIDE_PADDING = 100
LINE_SPACING = 10


# --- LLM rephraser -------------------------------------------------------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


# --- Instagram API -------------------------------------------------------
IG_LONG_LIVED_TOKEN = os.getenv("IG_LONG_LIVED_TOKEN", "")
IG_USER_ID = os.getenv("IG_USER_ID", "")
IG_APP_ID = os.getenv("IG_APP_ID", "")
IG_APP_SECRET = os.getenv("IG_APP_SECRET", "")
IG_API_VERSION = os.getenv("IG_API_VERSION", "v22.0")
IG_API_HOST = "https://graph.instagram.com"


# --- GitHub repo (image hosting) ----------------------------------------
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
IG_HANDLE = os.getenv("IG_HANDLE", "")


# --- Caption template ----------------------------------------------------
HASHTAGS = (
    "#dailyhoroscope #astrology #zodiac #horoscope #aries #taurus #gemini "
    "#cancer #leo #virgo #libra #scorpio #sagittarius #capricorn #aquarius "
    "#pisces #astro #vedic #rashichakra"
)


def assert_runtime_config() -> None:
    """Fail fast if required env vars are missing."""
    missing = [
        name
        for name, value in [
            ("IG_LONG_LIVED_TOKEN", IG_LONG_LIVED_TOKEN),
            ("IG_USER_ID", IG_USER_ID),
            ("GITHUB_REPO", GITHUB_REPO),
        ]
        if not value
    ]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "See .env.example."
        )
