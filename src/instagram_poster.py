"""Instagram CAROUSEL poster — Instagram Login flow (graph.instagram.com).

Three-step publish for a carousel:
1. POST /me/media for each image with is_carousel_item=true -> child container IDs
2. POST /me/media with media_type=CAROUSEL + children=[ids] + caption -> carousel container ID
3. POST /me/media_publish?creation_id=<carousel_id>

Note: Instagram limits carousels to up to 20 children (was 10 historically).
We post however many we have; if the API rejects 13, the workflow log will say so.
"""
from __future__ import annotations

import time
from urllib.parse import quote

import requests

from . import config


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


def post_carousel(image_urls: list[str], caption: str) -> str:
    """End-to-end: create children, wait, create carousel, wait, publish."""
    # 1. Children
    child_ids: list[str] = []
    for i, url in enumerate(image_urls):
        cid = create_child_container(url)
        child_ids.append(cid)
        print(f"[rashichakra] child {i + 1}/{len(image_urls)} container_id={cid}")

    # 2. Wait for each child to be ready before grouping
    for cid in child_ids:
        _poll_status(cid)

    # 3. Carousel parent
    carousel_id = create_carousel_container(child_ids, caption)
    print(f"[rashichakra] carousel container_id={carousel_id}")
    _poll_status(carousel_id)

    # 4. Publish
    media_id = publish(carousel_id)
    print(f"[rashichakra] published media_id={media_id}")
    return media_id
