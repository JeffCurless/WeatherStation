"""Button B: hour-by-hour forecast as a table -- one row per hour, columns
for weather, temperature, chance of rain, wind, and UV index. Row count is
however many fit the body height at the requested 20pt font, not forced to
match config.forecast_hours -- on this panel's body height that works out
to the full 10 hours, but the row budget is computed rather than hardcoded
so it degrades gracefully if either changes.
"""

import datetime

from .. import palette
from ..icons import CATEGORY_LABELS, category_for
from ..renderer import load_font, render_unavailable_body
from ..wind import compass_direction

# (key, header label, column weight, text alignment). Weights were sized
# against measured textlength() for the widest real values in each column
# (e.g. "Partly Cloudy", "12:00am", "23 km/h SW") at the 20pt bold font used
# throughout, not chosen by eye.
_COLUMNS = (
    ("time", "Time", 124, "left"),
    ("weather", "Weather", 210, "left"),
    ("temp", "Temp", 90, "center"),
    ("rain", "Rain", 92, "center"),
    ("wind", "Wind", 164, "center"),
    ("uv", "UV", 62, "center"),
)

_FONT_SIZE = 20
_HEADER_HEIGHT = 34
_ROW_HEIGHT = 34
_CELL_LEFT_PAD = 6
# (row height - font ascent+descent of ~24px at size 20) / 2, to vertically
# center each line of text within its row.
_TEXT_Y_PAD = 5


def render_body(draw, image, ctx, body_rect):
    hours = ctx.hourly
    if not hours:
        render_unavailable_body(draw, ctx, body_rect, what="hourly forecast")
        return
    _render_table(draw, hours, body_rect, ctx.units)


def _render_table(draw, hours, rect, units):
    x0, y0, x1, y1 = rect
    width = x1 - x0
    height = y1 - y0

    total_weight = sum(weight for _, _, weight, _ in _COLUMNS)
    col_widths = [width * weight / total_weight for _, _, weight, _ in _COLUMNS]
    col_x = [x0]
    for w in col_widths[:-1]:
        col_x.append(col_x[-1] + w)

    font = load_font(_FONT_SIZE, bold=True)
    wind_unit = "mph" if units == "fahrenheit" else "km/h"

    max_rows = max(1, (height - _HEADER_HEIGHT) // _ROW_HEIGHT)
    hours = hours[:max_rows]

    header_y = y0 + _TEXT_Y_PAD
    for (_, label, _weight, align), cx, cw in zip(_COLUMNS, col_x, col_widths):
        _draw_cell(draw, label, cx, cw, header_y, align, font, palette.BLACK)

    header_rule_y = y0 + _HEADER_HEIGHT - 4
    draw.line([(x0, header_rule_y), (x1, header_rule_y)], fill=palette.GRID_LINE, width=2)

    for i, hour in enumerate(hours):
        row_top = y0 + _HEADER_HEIGHT + i * _ROW_HEIGHT
        row_y = row_top + _TEXT_Y_PAD
        values = _row_values(hour, wind_unit)
        for (key, _label, _weight, align), cx, cw in zip(_COLUMNS, col_x, col_widths):
            text, fill = values[key]
            _draw_cell(draw, text, cx, cw, row_y, align, font, fill)

        rule_y = row_top + _ROW_HEIGHT - 4
        draw.line([(x0, rule_y), (x1, rule_y)], fill=palette.GRID_LINE, width=1)


def _row_values(hour, wind_unit):
    category = category_for(hour["weather_code"])
    weather_label = CATEGORY_LABELS.get(category, category.title())

    precip = hour.get("precip_probability")
    rain_label = "--" if precip is None else f"{precip}%"

    wind_speed = hour.get("wind_speed")
    if wind_speed is None:
        wind_label = "--"
    else:
        wind_dir = hour.get("wind_direction")
        dir_suffix = f" {compass_direction(wind_dir)}" if wind_dir is not None else ""
        wind_label = f"{round(wind_speed)} {wind_unit}{dir_suffix}"

    uv_index = hour.get("uv_index")
    uv_label = "--" if uv_index is None else str(round(uv_index))

    return {
        "time": (_format_hour_label(hour["time"]), palette.BLACK),
        "weather": (weather_label, palette.BLACK),
        "temp": (f'{round(hour["temperature"])}°', palette.BLACK),
        "rain": (rain_label, palette.BLUE),
        "wind": (wind_label, palette.BLACK),
        "uv": (uv_label, palette.BLACK),
    }


def _draw_cell(draw, text, x, col_width, y, align, font, fill):
    if align == "left":
        tx = x + _CELL_LEFT_PAD
    else:
        tw = draw.textlength(text, font=font)
        tx = x + (col_width - tw) / 2
    draw.text((tx, y), text, font=font, fill=fill)


def _format_hour_label(iso_str):
    try:
        dt = datetime.datetime.fromisoformat(iso_str)
        return dt.strftime("%I:%M%p").lstrip("0").lower()
    except ValueError:
        return iso_str
