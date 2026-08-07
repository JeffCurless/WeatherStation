"""Builds a PIL Image for a given page from the current weather state.

Owns shared chrome (header/footer, fonts, page dispatch) so each module
under pages/ only has to implement the body content for its page. Every
color used anywhere in this package must come from palette.py -- the panel
only supports six fixed colors, so there is deliberately no path here that
produces anything else (no gradients, no antialiased blending against
non-palette colors).
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from . import palette
from .inky_driver import DISPLAY_WIDTH, DISPLAY_HEIGHT

log = logging.getLogger("weather_station.renderer")

HEADER_HEIGHT = 44
FOOTER_HEIGHT = 26
MARGIN = 10

PAGE_TITLES = {"daily": "7-Day Forecast", "hourly": "Hourly Forecast"}

_FONT_REGULAR_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)
_FONT_BOLD_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)

_font_cache = {}


def load_font(size, bold=False):
    """Best-effort TrueType font loader with a bitmap-font fallback so
    rendering never crashes just because a font package isn't installed on
    a particular device image."""
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]

    for path in (_FONT_BOLD_CANDIDATES if bold else _FONT_REGULAR_CANDIDATES):
        if Path(path).exists():
            try:
                font = ImageFont.truetype(path, size)
                _font_cache[key] = font
                return font
            except OSError:
                continue

    try:
        font = ImageFont.load_default(size=size)  # Pillow >= 9.2
    except TypeError:
        font = ImageFont.load_default()
    _font_cache[key] = font
    return font


@dataclass
class RenderContext:
    """Everything a page body needs to draw itself. Built fresh each poll
    cycle in main.py (or by scripts/render_preview.py) from the current
    weather_state."""
    page_name: str = "daily"
    subpage: int = 0
    button_page_map: dict = field(default_factory=lambda: {"A": "daily", "B": "hourly"})
    now: int = field(default_factory=lambda: int(time.time()))
    daily: Optional[list] = None
    hourly: Optional[list] = None
    weather_updated_at: Optional[int] = None
    units: str = "fahrenheit"


def format_ago(seconds):
    if seconds is None:
        return "never"
    if seconds < 60:
        return f"{int(seconds)}s ago"
    if seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    return f"{int(seconds // 3600)}h ago"


def render_unavailable_body(draw, ctx, body_rect, what="forecast"):
    x0, y0, x1, y1 = body_rect
    font = load_font(16)
    if ctx.weather_updated_at:
        updated = format_ago(ctx.now - ctx.weather_updated_at)
    else:
        updated = "never"
    lines = [
        f"{what.capitalize()} unavailable.",
        "",
        f"Last successful fetch: {updated}",
    ]
    y = y0
    for line in lines:
        if line:
            draw.text((x0, y), line, font=font, fill=palette.BLACK)
        y += 22


def _draw_header(draw, ctx):
    title = PAGE_TITLES.get(ctx.page_name, ctx.page_name.title())
    font_title = load_font(22, bold=True)
    font_meta = load_font(14)

    draw.text((MARGIN, 8), title, font=font_title, fill=palette.FOREGROUND)

    updated_at = time.strftime("%H:%M:%S", time.localtime(ctx.now))
    meta = f"updated {updated_at}"
    w = draw.textlength(meta, font=font_meta)
    draw.text((DISPLAY_WIDTH - MARGIN - w, 14), meta, font=font_meta, fill=palette.FOREGROUND)

    draw.line(
        [(MARGIN, HEADER_HEIGHT - 2), (DISPLAY_WIDTH - MARGIN, HEADER_HEIGHT - 2)],
        fill=palette.GRID_LINE, width=2,
    )


def _draw_footer(draw, ctx):
    y = DISPLAY_HEIGHT - FOOTER_HEIGHT
    font = load_font(13)
    draw.line([(MARGIN, y), (DISPLAY_WIDTH - MARGIN, y)], fill=palette.GRID_LINE, width=1)

    buttons_text = "  ".join(
        f"{btn}:{page.title()}" for btn, page in sorted(ctx.button_page_map.items())
    )
    draw.text((MARGIN, y + 5), buttons_text, font=font, fill=palette.FOREGROUND)


def render_page(page_name, ctx):
    from .pages import daily, hourly  # avoid import cycle at module load

    builders = {
        "daily": daily.render_body,
        "hourly": hourly.render_body,
    }

    image = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), palette.BACKGROUND)
    draw = ImageDraw.Draw(image)
    # Pillow antialiases TrueType glyph edges by default (blended in-between
    # colors along the outline). On a 6-fixed-color e-ink panel there's no
    # such thing as an in-between color -- each of those blended edge pixels
    # gets quantized to whichever of the 6 ink colors happens to be nearest,
    # which is inconsistent pixel-to-pixel and reads as speckled/pixelated.
    # "1" disables antialiasing so every glyph pixel is either fully the
    # fill color or fully background.
    draw.fontmode = "1"

    _draw_header(draw, ctx)
    body_rect = (MARGIN, HEADER_HEIGHT + 6, DISPLAY_WIDTH - MARGIN, DISPLAY_HEIGHT - FOOTER_HEIGHT - 4)

    builder = builders.get(page_name, daily.render_body)
    try:
        builder(draw, image, ctx, body_rect)
    except Exception:
        log.exception("failed to render page %s, falling back to blank body", page_name)

    _draw_footer(draw, ctx)
    return image
