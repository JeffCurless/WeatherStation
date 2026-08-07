"""Button A (default page): 7-day forecast from Open-Meteo, with extra
detail for today.
"""

import datetime

from .. import palette
from ..icons import CATEGORY_LABELS, category_for, draw_icon
from ..renderer import load_font, render_unavailable_body
from ..wind import compass_direction


def render_body(draw, image, ctx, body_rect):
    days = ctx.daily
    if not days:
        render_unavailable_body(draw, ctx, body_rect, what="forecast")
        return

    x0, y0, x1, y1 = body_rect
    height = y1 - y0

    today_h = int(height * 0.42)
    _render_today(draw, days[0], (x0, y0, x1, y0 + today_h))

    forecast_rect = (x0, y0 + today_h + 10, x1, y1)
    _render_forecast_row(draw, days[1:], forecast_rect)


def _render_today(draw, day, rect):
    x0, y0, x1, y1 = rect
    icon_size = min(y1 - y0, 120)
    icon_box = (x0, y0, x0 + icon_size, y0 + icon_size)
    category = category_for(day["weather_code"])
    draw_icon(draw, icon_box, category)

    text_x = x0 + icon_size + 20
    font_big = load_font(40, bold=True)
    font_med = load_font(18)
    font_label = load_font(16, bold=True)

    draw.text((text_x, y0), "Today", font=font_label, fill=palette.BLACK)

    hi = round(day["hi"])
    lo = round(day["lo"])
    draw.text((text_x, y0 + 26), f"{hi}° / {lo}°", font=font_big, fill=palette.BLACK)

    cond_label = CATEGORY_LABELS.get(category, category.title())
    parts = [cond_label]

    precip = day.get("precip_probability")
    if precip is not None:
        parts.append(f"{precip}% precip")

    wind_speed = day.get("wind_speed")
    if wind_speed is not None:
        wind_dir = day.get("wind_direction")
        dir_suffix = f" {compass_direction(wind_dir)}" if wind_dir is not None else ""
        parts.append(f"{round(wind_speed)}mph{dir_suffix}")

    uv_index = day.get("uv_index")
    if uv_index is not None:
        parts.append(f"UV {round(uv_index)}")

    meta = "  |  ".join(parts)
    draw.text((text_x, y0 + 26 + 46), meta, font=font_med, fill=palette.BLACK)


def _render_forecast_row(draw, days, rect):
    x0, y0, x1, y1 = rect
    if not days:
        return
    width = x1 - x0

    max_cols = max(1, width // 90)
    days = days[:max_cols]
    col_w = width // len(days)
    icon_size = min(col_w - 16, y1 - y0 - 60, 60)

    # Bold and larger than a naive first pass -- thin regular-weight text at
    # small sizes reads "spidery"/hard to read on the real e-ink panel.
    font_day = load_font(18, bold=True)
    font_temp = load_font(17, bold=True)
    font_precip = load_font(15, bold=True)

    for i, day in enumerate(days):
        col_center = x0 + i * col_w + col_w // 2

        label = _format_weekday(day["date"])
        lw = draw.textlength(label, font=font_day)
        draw.text((col_center - lw / 2, y0), label, font=font_day, fill=palette.BLACK)

        icon_box = (
            col_center - icon_size // 2, y0 + 26,
            col_center + icon_size // 2, y0 + 26 + icon_size,
        )
        draw_icon(draw, icon_box, category_for(day["weather_code"]))

        hi = round(day["hi"])
        lo = round(day["lo"])
        temp_label = f"{hi}°/{lo}°"
        tw = draw.textlength(temp_label, font=font_temp)
        temp_y = y0 + 32 + icon_size
        draw.text((col_center - tw / 2, temp_y), temp_label, font=font_temp, fill=palette.BLACK)

        line_y = temp_y + 22

        precip = day.get("precip_probability")
        if precip is not None:
            line_y = _draw_centered(draw, f"{precip}%", col_center, line_y, font_precip, palette.BLUE)

        wind_speed = day.get("wind_speed")
        if wind_speed is not None:
            wind_dir = day.get("wind_direction")
            dir_suffix = f" {compass_direction(wind_dir)}" if wind_dir is not None else ""
            line_y = _draw_centered(
                draw, f"{round(wind_speed)}mph{dir_suffix}", col_center, line_y, font_precip, palette.BLACK,
            )

        uv_index = day.get("uv_index")
        if uv_index is not None:
            _draw_centered(draw, f"UV {round(uv_index)}", col_center, line_y, font_precip, palette.BLACK)


def _format_weekday(date_str):
    try:
        return datetime.date.fromisoformat(date_str).strftime("%a")
    except ValueError:
        return date_str


_LINE_HEIGHT = 20


def _draw_centered(draw, text, col_center, y, font, fill):
    """Draws text centered on col_center at y, returns the y for the next
    stacked line below it."""
    w = draw.textlength(text, font=font)
    draw.text((col_center - w / 2, y), text, font=font, fill=fill)
    return y + _LINE_HEIGHT
