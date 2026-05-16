"""Daily orchestrator with two stages so CI can commit-and-push between them.

Subcommands:
  render          Fetch all 12 horoscopes, render cover + 12 zodiac slides into posts/<date>/.
                  If any scrape fails, exits 0 cleanly and writes no pending file (skip day).
  publish         Read state/_pending.json, post to Instagram (splitting into 10-image carousels if needed).
                  If no pending file (because render skipped), exits 0 cleanly.
  all             render + publish in one go (for local testing).
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from . import config, horoscope_loader, image_renderer, instagram_poster

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger(__name__)

PENDING_FILE = config.STATE_DIR / "_pending.json"
POSTED_FILE = config.STATE_DIR / "posted.json"


def build_caption(today: date, horoscopes: list[dict]) -> str:
    lines = [
        f"Daily Horoscope — {today.strftime('%B %-d, %Y')}",
        "",
        "Swipe to find your sign ✨",
        "",
    ]
    for h in horoscopes:
        lines.append(f"{h['name_en']} ({h['date_range']})")
    if config.IG_HANDLE:
        lines.extend(["", f"Follow {config.IG_HANDLE} for daily horoscopes."])
    lines.extend(["", config.HASHTAGS])
    return "\n".join(lines)


def render_step() -> dict | None:
    today = date.today()
    log.info("rendering for %s", today.isoformat())

    try:
        horoscopes = horoscope_loader.horoscope_all()
    except horoscope_loader.SkipDay as e:
        log.warning("SKIPPING today's post: %s", e)
        return None

    out_dir = config.POSTS_DIR / today.isoformat()
    paths = image_renderer.render_all(today, horoscopes, out_dir)

    image_relpaths = [str(p.relative_to(config.ROOT)) for p in paths]
    caption = build_caption(today, horoscopes)

    info = {
        "date": today.isoformat(),
        "image_relpaths": image_relpaths,
        "caption": caption,
        "horoscopes": [
            {"slug": h["slug"], "horoscope": h["horoscope"]}
            for h in horoscopes
        ],
        "rendered_at": datetime.now(timezone.utc).isoformat(),
    }
    PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with PENDING_FILE.open("w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    log.info("wrote pending manifest -> %s", PENDING_FILE)
    return info


def publish_step(info: dict | None = None, part: int | None = None) -> list[str] | None:
    """Publish the carousel. If part=1, post only the first batch and keep _pending.json.
    If part=2, post only the second batch and clean up. If part=None, post everything."""
    if info is None:
        if not PENDING_FILE.exists():
            log.info("no pending render, nothing to publish (likely a skipped day)")
            return None
        with PENDING_FILE.open("r", encoding="utf-8") as f:
            info = json.load(f)

    config.assert_runtime_config()

    image_urls = [instagram_poster.public_image_url(p) for p in info["image_relpaths"]]
    log.info("publishing %d image(s) to Instagram (part=%s)", len(image_urls), part or "all")

    try:
        media_ids = instagram_poster.post_carousel(image_urls, info["caption"], part=part)
    except RuntimeError as e:
        if "403" in str(e) and part == 2:
            log.warning("part 2 publish blocked by Instagram (rate limit): %s", e)
            log.warning("part 1 is already live — skipping part 2 gracefully")
            if PENDING_FILE.exists():
                PENDING_FILE.unlink()
            return None
        raise

    log.info("published %d Instagram post(s): %s", len(media_ids), ", ".join(media_ids))

    _record_post(info, media_ids)
    # Only clean up after the final part so part2 workflow can still read the file.
    if part != 1 and PENDING_FILE.exists():
        PENDING_FILE.unlink()
    return media_ids


def _record_post(info: dict, media_ids: list[str]) -> None:
    POSTED_FILE.parent.mkdir(parents=True, exist_ok=True)
    if POSTED_FILE.exists():
        with POSTED_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"posted": []}
    data.setdefault("posted", []).append(
        {
            "date": info["date"],
            "ig_media_ids": media_ids,
            "ig_media_id": media_ids[0],
            "instagram_posts": len(media_ids),
            "image_count": len(info["image_relpaths"]),
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    with POSTED_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Rashichakra daily horoscope poster.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("render", help="Fetch + render only.")
    pub = sub.add_parser("publish", help="Publish previously-rendered carousel.")
    pub.add_argument("--part", type=int, choices=[1, 2], default=None,
                     help="Post only part 1 or part 2 (omit to post both).")
    sub.add_parser("all", help="Render and publish in one go.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.cmd == "render":
        render_step()
    elif args.cmd == "publish":
        publish_step(part=getattr(args, "part", None))
    elif args.cmd == "all":
        info = render_step()
        if info is not None:
            publish_step(info)
    return 0


if __name__ == "__main__":
    sys.exit(main())
