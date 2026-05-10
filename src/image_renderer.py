"""Render zodiac slides (text overlay on user-provided templates) and the cover slide (date stamp)."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from . import config


def _cover_template_path() -> Path:
    """Resolve cover slide template; prefers COVER_IMAGE env, then common filenames."""
    d = config.ZODIAC_IMAGES_DIR
    if config.COVER_IMAGE:
        p = d / config.COVER_IMAGE
        if p.is_file():
            return p
        raise FileNotFoundError(
            f"COVER_IMAGE set but file missing: {p}"
        )
    for name in ("cover.jpg", "cover.jpeg", "cover.png"):
        p = d / name
        if p.is_file():
            return p
    raise FileNotFoundError(
        f"No cover template in {d}. Add cover.jpg, cover.jpeg, or cover.png, "
        "or set COVER_IMAGE to a filename in that folder."
    )


def _load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not path.exists():
        raise FileNotFoundError(
            f"Font not found at {path}. Run scripts/download_fonts.sh first."
        )
    return ImageFont.truetype(str(path), size)


def _wrap(text: str, font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw, max_w: int) -> list[str]:
    out: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        current = ""
        for w in words:
            cand = (current + " " + w).strip()
            bbox = draw.textbbox((0, 0), cand, font=font)
            if bbox[2] - bbox[0] <= max_w:
                current = cand
            else:
                if current:
                    out.append(current)
                current = w
        if current:
            out.append(current)
    return out


def _draw_block(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    center_x: int,
    top_y: int,
    line_spacing: int,
    fill: tuple[int, int, int],
    shadow: bool = True,
) -> int:
    y = top_y
    for line in lines:
        bbox = draw.textbbox((0, 0), line or " ", font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = center_x - w // 2
        if shadow:
            draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 200))
        draw.text((x, y), line, font=font, fill=fill)
        y += h + line_spacing
    return y


def _fit_to_canvas(img: Image.Image) -> Image.Image:
    """Scale + center-crop the image to (IMG_WIDTH, IMG_HEIGHT)."""
    target_ratio = config.IMG_WIDTH / config.IMG_HEIGHT
    src_ratio = img.width / img.height
    if src_ratio > target_ratio:
        new_width = int(img.height * target_ratio)
        left = (img.width - new_width) // 2
        img = img.crop((left, 0, left + new_width, img.height))
    else:
        new_height = int(img.width / target_ratio)
        top = (img.height - new_height) // 2
        img = img.crop((0, top, img.width, top + new_height))
    return img.resize((config.IMG_WIDTH, config.IMG_HEIGHT), Image.LANCZOS)


def render_zodiac_slide(
    template_path: Path,
    zodiac: dict,
    horoscope_text: str,
    output_path: Path,
) -> Path:
    """Overlay the zodiac name + daily horoscope on the right-side panel."""
    base = Image.open(template_path).convert("RGB")
    base = _fit_to_canvas(base).convert("RGBA")

    # Dark panel covering the right portion of the image so zodiac art shows on the left.
    panel_x = int(config.IMG_WIDTH * config.TEXT_PANEL_X_FRAC)
    panel = Image.new("RGBA", (config.IMG_WIDTH, config.IMG_HEIGHT), (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(panel)
    pdraw.rectangle(
        [(panel_x, 0), (config.IMG_WIDTH, config.IMG_HEIGHT)],
        fill=(0, 0, 0, config.TEXT_PANEL_OPACITY),
    )
    img = Image.alpha_composite(base, panel)
    draw = ImageDraw.Draw(img)

    panel_w = config.IMG_WIDTH - panel_x
    center_x = panel_x + panel_w // 2
    max_text_w = panel_w - 2 * config.TEXT_PANEL_PADDING

    name_font = _load_font(config.FONT_DISPLAY, config.SIGN_NAME_FONT_SIZE)
    body_font = _load_font(config.FONT_BODY_REGULAR, config.HOROSCOPE_FONT_SIZE)
    handle_font = _load_font(config.FONT_BODY_REGULAR, config.HANDLE_FONT_SIZE)

    name_text = zodiac['name_en']

    # Sign name — vertically centered in the upper quarter of the panel.
    bbox = draw.textbbox((0, 0), name_text, font=name_font)
    name_h = bbox[3] - bbox[1]
    name_y = int(config.IMG_HEIGHT * 0.12)
    _draw_block(draw, [name_text], name_font, center_x, name_y, 0, config.TEXT_COLOR)

    # Horoscope body, wrapped and centered in the remaining vertical space.
    lines = _wrap(horoscope_text, body_font, draw, max_text_w)
    body_y = name_y + name_h + 40

    # Vertically center the body block between the name and the handle area.
    handle_reserve = 80 if config.IG_HANDLE else 0
    available_h = config.IMG_HEIGHT - body_y - handle_reserve - 40
    line_h = body_font.size + config.LINE_SPACING
    block_h = len(lines) * line_h
    if block_h < available_h:
        body_y += (available_h - block_h) // 2

    _draw_block(draw, lines, body_font, center_x, body_y, config.LINE_SPACING, config.TEXT_COLOR)

    # @handle pinned to bottom-center of the panel.
    if config.IG_HANDLE:
        bbox = draw.textbbox((0, 0), config.IG_HANDLE, font=handle_font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = center_x - w // 2
        y = config.IMG_HEIGHT - h - 30
        draw.text((x + 1, y + 1), config.IG_HANDLE, font=handle_font, fill=(0, 0, 0))
        draw.text((x, y), config.IG_HANDLE, font=handle_font, fill=config.TEXT_COLOR)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=92, optimize=True)
    return output_path


def render_cover_slide(
    cover_template_path: Path,
    today: date,
    output_path: Path,
) -> Path:
    """Overlay today's date on the cover template."""
    base = Image.open(cover_template_path).convert("RGB")
    base = _fit_to_canvas(base).convert("RGBA")
    img = base
    draw = ImageDraw.Draw(img)

    date_font = _load_font(config.FONT_DISPLAY, config.DATE_FONT_SIZE)
    date_str = today.strftime("%B %-d, %Y")  # e.g. May 9, 2026

    # Centered, lower third
    bbox = draw.textbbox((0, 0), date_str, font=date_font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (config.IMG_WIDTH - w) // 2
    y = int(config.IMG_HEIGHT * 0.78) - h // 2
    # Drop shadow + outline for legibility on any background
    for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
        draw.text((x + ox, y + oy), date_str, font=date_font, fill=(0, 0, 0))
    draw.text((x, y), date_str, font=date_font, fill=config.DATE_COLOR)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, "JPEG", quality=92, optimize=True)
    return output_path


def render_all(
    today: date,
    horoscopes: Iterable[dict],
    output_dir: Path,
) -> list[Path]:
    """Render the cover + 12 zodiac slides. Returns ordered list of paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    cover_template = _cover_template_path()
    cover_out = output_dir / "00-cover.jpg"
    render_cover_slide(cover_template, today, cover_out)
    paths.append(cover_out)

    for i, h in enumerate(horoscopes, start=1):
        template = config.ZODIAC_IMAGES_DIR / h["image_filename"]
        out = output_dir / f"{i:02d}-{h['slug']}.jpg"
        render_zodiac_slide(template, h, h["horoscope"], out)
        paths.append(out)
    return paths
