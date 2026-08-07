"""WMO weather-code categorization and hand-drawn PIL icon primitives,
shared by pages/daily.py and pages/hourly.py.

Icons are drawn from PIL primitives using only the panel's 6 fixed colors
(palette.py) rather than photographic/bitmap assets, so nothing here ever
needs dithering or antialiasing. Two legibility lessons baked in below were
confirmed on real e-ink hardware (in the sibling netstatus project, which
uses the same panel):

- Icons that only differ by a thin detail don't read as visually distinct
  at a glance, especially across several similar entries in a row. Rain's
  cloud is filled solid blue (not just outlined with a few faint lines) so
  it differs by shape/color, not just detail, from a plain "cloudy" icon.
"""

import math

from PIL import Image, ImageDraw

from . import palette

WMO_CODE_CATEGORY = {
    0: "clear",
    1: "partly_cloudy", 2: "partly_cloudy",
    3: "cloudy",
    45: "fog", 48: "fog",
    51: "rain", 53: "rain", 55: "rain", 56: "rain", 57: "rain",
    61: "rain", 63: "rain", 65: "rain", 66: "rain", 67: "rain",
    80: "rain", 81: "rain", 82: "rain",
    71: "snow", 73: "snow", 75: "snow", 77: "snow", 85: "snow", 86: "snow",
    95: "storm", 96: "storm", 99: "storm",
}

CATEGORY_LABELS = {
    "clear": "Clear",
    "partly_cloudy": "Partly Cloudy",
    "cloudy": "Cloudy",
    "fog": "Fog",
    "rain": "Rain",
    "snow": "Snow",
    "storm": "Storm",
}


def category_for(weather_code):
    return WMO_CODE_CATEGORY.get(weather_code, "cloudy")


def draw_icon(draw, box, category):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    w, h = x1 - x0, y1 - y0
    r = min(w, h) // 2

    if category == "clear":
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=palette.YELLOW, outline=palette.BLACK)
    elif category == "partly_cloudy":
        sun_r = int(r * 0.7)
        sx, sy = cx - int(r * 0.3), cy - int(r * 0.3)
        draw.ellipse([sx - sun_r, sy - sun_r, sx + sun_r, sy + sun_r], fill=palette.YELLOW, outline=palette.BLACK)
        _draw_cloud(draw, (cx - int(r * 0.9), cy - int(r * 0.1), x1, y1))
    elif category == "cloudy":
        _draw_cloud_dithered(draw, box)
    elif category == "fog":
        _draw_cloud(draw, (x0, y0, x1, cy))
        step = max(4, h // 6)
        for ly in range(cy, y1, step):
            draw.line([(x0, ly), (x1, ly)], fill=palette.BLACK, width=2)
    elif category == "rain":
        _draw_cloud(draw, (x0, y0, x1, cy + h // 6), fill=palette.BLUE)
        drop_y0 = cy + h // 4
        step = max(5, w // 5)
        for dx in range(x0 + w // 6, x1, step):
            draw.line([(dx, drop_y0), (dx - 4, y1)], fill=palette.BLUE, width=4)
    elif category == "snow":
        _draw_cloud(draw, (x0, y0, x1, cy + h // 6))
        flake_y = cy + h // 3
        step = max(8, w // 4)
        flake_size = max(4, w // 10)
        for dx in range(x0 + w // 6, x1, step):
            _draw_asterisk(draw, dx, flake_y, flake_size)
    elif category == "storm":
        _draw_cloud(draw, (x0, y0, x1, cy))
        bolt = [
            (cx, cy - h // 10),
            (cx - w // 8, cy + h // 4),
            (cx, cy + h // 4),
            (cx - w // 10, y1),
            (cx + w // 6, cy + h // 8),
            (cx, cy + h // 8),
        ]
        draw.polygon(bolt, fill=palette.YELLOW, outline=palette.BLACK)
    else:
        draw.rectangle(box, outline=palette.BLACK, width=2)


def _cloud_ellipses(box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    body_y0 = y0 + h // 3
    return (
        [x0, body_y0, x0 + int(w * 0.6), y1],
        [x0 + int(w * 0.3), body_y0 - int(h * 0.2), x0 + int(w * 0.9), y1],
        [x0 + int(w * 0.15), body_y0 + int(h * 0.1), x0 + int(w * 0.75), y1],
    )


def _draw_cloud(draw, box, fill=palette.WHITE):
    for ellipse_box in _cloud_ellipses(box):
        draw.ellipse(ellipse_box, fill=fill, outline=palette.BLACK)


# Classic 4x4 Bayer ordered-dither matrix (values 0-15, exactly 8 of 16
# cells below the midpoint -> exact 50/50 black/white density). Used
# in-house instead of a whole-image dithering library since this only ever
# dithers one hand-drawn shape (the "cloudy" icon's fill) with two colors,
# not a continuous-tone photo across the full 6-color palette.
_BAYER_4 = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)


def _dither_fill_ellipse(draw, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return
    mask = Image.new("1", (w + 1, h + 1))
    ImageDraw.Draw(mask).ellipse([0, 0, w, h], fill=1)
    mask_px = mask.load()
    # Keyed by absolute page coordinates (not local x0/y0-relative offsets)
    # so the dither phase lines up seamlessly across the cloud's three
    # overlapping ellipses instead of showing a visible seam where they meet.
    for dy in range(h + 1):
        row = _BAYER_4[(y0 + dy) % 4]
        for dx in range(w + 1):
            if mask_px[dx, dy]:
                color = palette.BLACK if row[(x0 + dx) % 4] < 8 else palette.WHITE
                draw.point((x0 + dx, y0 + dy), fill=color)


def _draw_cloud_dithered(draw, box):
    # Dither+outline each ellipse in turn (not one shared mask, then all
    # outlines at the end) so a later ellipse's fill still hides an earlier
    # ellipse's outline where they overlap, exactly like _draw_cloud's
    # layering -- otherwise inner seam arcs would show through the cloud
    # body instead of a clean union silhouette.
    for ellipse_box in _cloud_ellipses(box):
        _dither_fill_ellipse(draw, ellipse_box)
        draw.ellipse(ellipse_box, outline=palette.BLACK)


def _draw_asterisk(draw, cx, cy, size):
    for angle in (0, 60, 120):
        rad = math.radians(angle)
        dx = int(size * math.cos(rad))
        dy = int(size * math.sin(rad))
        draw.line([(cx - dx, cy - dy), (cx + dx, cy + dy)], fill=palette.BLUE, width=2)
