#!/usr/bin/env python3
"""Render a grid of every palette background color against several text
color/weight/size combinations, to settle contrast questions on the real
panel empirically instead of guessing from a PNG on a normal screen.

    python3 scripts/render_color_swatch.py --output swatch.png
    python3 scripts/render_color_swatch.py --real     # push straight to the Inky panel

Each row is one of the 6 ink colors; each column is a text style
(color/weight/size) applied to a realistic sample temperature string. Look
at the real panel (not the PNG -- e-ink contrast doesn't reliably match a
normal screen) and note which column reads best for each row.
"""

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from weather_station import inky_driver, palette  # noqa: E402
from weather_station.renderer import load_font  # noqa: E402

SAMPLE_TEXT = "68°"

ROWS = (
    ("BLACK", palette.BLACK),
    ("WHITE", palette.WHITE),
    ("RED", palette.RED),
    ("GREEN", palette.GREEN),
    ("BLUE", palette.BLUE),
    ("YELLOW", palette.YELLOW),
)

# (column label, text color, bold, font size)
COLUMNS = (
    ("blk 14", palette.BLACK, False, 14),
    ("wht 14", palette.WHITE, False, 14),
    ("blk B14", palette.BLACK, True, 14),
    ("wht B14", palette.WHITE, True, 14),
    ("blk B20", palette.BLACK, True, 20),
    ("wht B20", palette.WHITE, True, 20),
)

LABEL_COL_W = 90
HEADER_H = 26


def build_swatch():
    width, height = inky_driver.DISPLAY_WIDTH, inky_driver.DISPLAY_HEIGHT
    image = Image.new("RGB", (width, height), palette.WHITE)
    draw = ImageDraw.Draw(image)
    draw.fontmode = "1"  # same antialiasing fix as renderer.py -- crisp, no speckling

    col_w = (width - LABEL_COL_W) // len(COLUMNS)
    row_h = (height - HEADER_H) // len(ROWS)
    header_font = load_font(11, bold=True)

    for c, (col_label, _text_color, _bold, _size) in enumerate(COLUMNS):
        cx = LABEL_COL_W + c * col_w
        draw.text((cx + 4, 6), col_label, font=header_font, fill=palette.BLACK)

    for r, (row_label, bg) in enumerate(ROWS):
        ry = HEADER_H + r * row_h
        draw.text((4, ry + row_h // 2 - 7), row_label, font=header_font, fill=palette.BLACK)

        for c, (_col_label, text_color, bold, size) in enumerate(COLUMNS):
            cx = LABEL_COL_W + c * col_w
            cell_font = load_font(size, bold=bold)
            draw.rectangle([cx, ry, cx + col_w - 2, ry + row_h - 2], fill=bg, outline=palette.BLACK)
            tw = draw.textlength(SAMPLE_TEXT, font=cell_font)
            th = getattr(cell_font, "size", size)
            draw.text(
                (cx + (col_w - tw) / 2, ry + (row_h - th) / 2),
                SAMPLE_TEXT, font=cell_font, fill=text_color,
            )

    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", default="swatch.png", help="PNG path (ignored with --real)")
    parser.add_argument("--real", action="store_true", help="push directly to real Inky hardware instead of writing a PNG")
    args = parser.parse_args()

    image = build_swatch()

    if args.real:
        driver = inky_driver.get_driver(mock_output_path=None)
        driver.set_image(image)
        driver.show()
        print("pushed swatch to the real display")
    else:
        image.save(args.output)
        print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
