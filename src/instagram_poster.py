"""Instagram CAROUSEL poster — Instagram Login flow (graph.instagram.com).

Three-step publish for a carousel:
1. POST /me/media for each image with is_carousel_item=true -> child container IDs
2. POST /me/media with media_type=CAROUSEL + children=[ids] + caption -> carousel container ID
3. POST /me/media_publish?creation_id=<carousel_id>

Meta limits one carousel to at most 10 images (`children` is up to 10 IDs).

Rashichakra publishes **two** feed posts: **7** images (cover + six zodiac slides),
then **6** images (remaining six signs). The second post uses a short part-2 caption.
"""
from __future__ import annotations

import time
from urllib.parse import quote

import requests

from . import config

# https://developers.facebook.com/docs/instagram-platform/content-publishing/
# "children — A comma separated list of up to 10 container IDs"
MAX_CAROUSEL_ITEMS = 10

# Two IG posts of 7 slides each: cover + six signs. Second post repeats the same cover
# image URL, then Libra→Pisces (same cover JPG hosted twice in the carousel).
FIRST_POST_IMAGE_COUNT = 7


def public_image_url(image_relpath: str) -> str:
    if not config.GITHUB_REPO:
        raise RuntimeError("GITHUB_REPO env var must be set, e.g. 'rayyanop61/rashichakra'.")
    safe_path = quote(image_relpath.lstrip("/"))
    return (
        f"https://raw.githubusercontent.com/{config.GITHUB_REPO}/"
        f"{config.GITHUB_BRANCH}/{safe_path}"
    )


def _api_url(path: str) -> str:
    return f"{config.IG_API_HOST}/{config.IG_API_VERSION}/{path.lstrip('/')}"


def _check(resp: requests.Response, ctx: str) -> dict:
    if resp.status_code >= 400:
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        raise RuntimeError(f"{ctx} -> HTTP {resp.status_code}: {err}")
    return resp.json()


def _poll_status(container_id: str, timeout_s: int = 180) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        resp = requests.get(
            _api_url(container_id),
            params={
                "fields": "status_code,status",
                "access_token": config.IG_LONG_LIVED_TOKEN,
            },
            timeout=30,
        )
        data = _check(resp, "poll_status")
        status = data.get("status_code") or data.get("status", "")
        if status in ("FINISHED", "PUBLISHED"):
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Container {container_id} failed: {data}")
        time.sleep(3)
    raise TimeoutError(f"Container {container_id} not ready after {timeout_s}s")


def create_child_container(image_url: str) -> str:
    """Create a single child media container for a carousel item."""
    resp = requests.post(
        _api_url("me/media"),
        data={
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": config.IG_LONG_LIVED_TOKEN,
        },
        timeout=60,
    )
    payload = _check(resp, "create_child_container")
    cid = payload.get("id")
    if not cid:
        raise RuntimeError(f"No id in response: {payload}")
    return cid


def _continuation_caption(part: int, total_parts: int) -> str:
    return (
        f"Daily horoscope — part {part}/{total_parts} ✨\n\n"
        "Swipe for the remaining signs.\n\n"
        f"{config.HASHTAGS}"
    )


def create_standalone_image_container(image_url: str, caption: str) -> str:
    """Single-image post (not a carousel). Used when a batch has exactly one URL."""
    resp = requests.post(
        _api_url("me/media"),
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": config.IG_LONG_LIVED_TOKEN,
        },
        timeout=60,
    )
    payload = _check(resp, "create_standalone_image_container")
    cid = payload.get("id")
    if not cid:
        raise RuntimeError(f"No id in response: {payload}")
    return cid


def create_carousel_container(child_ids: list[str], caption: str) -> str:
    resp = requests.post(
        _api_url("me/media"),
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": config.IG_LONG_LIVED_TOKEN,
        },
        timeout=60,
    )
    payload = _check(resp, "create_carousel_container")
    cid = payload.get("id")
    if not cid:
        raise RuntimeError(f"No id in response: {payload}")
    return cid


def publish(creation_id: str) -> str:
    resp = requests.post(
        _api_url("me/media_publish"),
        data={
            "creation_id": creation_id,
            "access_token": config.IG_LONG_LIVED_TOKEN,
        },
        timeout=60,
    )
    return _check(resp, "publish").get("id", "")


def _post_single_carousel(image_urls: list[str], caption: str) -> str:
    """One carousel post with 2–10 images."""
    if not (2 <= len(image_urls) <= MAX_CAROUSEL_ITEMS):
        raise ValueError(
            f"carousel batch must have 2–{MAX_CAROUSEL_ITEMS} images, got {len(image_urls)}"
        )
    child_ids: list[str] = []
    for i, url in enumerate(image_urls):
        cid = create_child_container(url)
        child_ids.append(cid)
        print(f"[rashichakra] child {i + 1}/{len(image_urls)} container_id={cid}")

    for cid in child_ids:
        _poll_status(cid)

    carousel_id = create_carousel_container(child_ids, caption)
    print(f"[rashichakra] carousel container_id={carousel_id}")
    _poll_status(carousel_id)

    media_id = publish(carousel_id)
    print(f"[rashichakra] published media_id={media_id}")
    return media_id


def _post_standalone_image(image_url: str, caption: str) -> str:
    """Single-image feed post."""
    cid = create_standalone_image_container(image_url, caption)
    print(f"[rashichakra] standalone image container_id={cid}")
    _poll_status(cid)
    media_id = publish(cid)
    print(f"[rashichakra] published media_id={media_id}")
    return media_id


def post_carousel(image_urls: list[str], caption: str) -> list[str]:
    """Publish feed content in two posts when there are more than 7 images.

    Slide order from `render_all` is: cover, then zodiacs.json order (Aries … Pisces).
    Post 1: cover + first six signs. Post 2: **same cover** again + last six signs (7 slides).
    """
    if not image_urls:
        raise ValueError("post_carousel: empty image_urls")

    n = len(image_urls)

    if n <= FIRST_POST_IMAGE_COUNT:
        if n == 1:
            return [_post_standalone_image(image_urls[0], caption)]
        return [_post_single_carousel(image_urls, caption)]

    cover_url = image_urls[0]
    first = image_urls[:FIRST_POST_IMAGE_COUNT]
    tail = image_urls[FIRST_POST_IMAGE_COUNT:]
    # Second carousel: repeat cover so both posts open with the date slide.
    second = [cover_url] + tail

    if len(second) > MAX_CAROUSEL_ITEMS:
        raise ValueError(
            f"second batch has {len(second)} images; Meta allows at most "
            f"{MAX_CAROUSEL_ITEMS} per carousel — shorten render output or adjust splitting."
        )

    media_ids: list[str] = []

    print(
        f"[rashichakra] post 1/2: {len(first)} images (cover + six signs)"
    )
    media_ids.append(_post_single_carousel(first, caption))

    print(
        f"[rashichakra] post 2/2: {len(second)} images (cover + remaining signs)"
    )
    cap2 = _continuation_caption(2, 2)
    media_ids.append(_post_single_carousel(second, cap2))

    return media_ids
