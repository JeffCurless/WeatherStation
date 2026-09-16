#!/usr/bin/env python3
"""Render a single weather-station page to a PNG, no hardware needed.

The fast local-iteration loop: eyeball the resulting PNG after any change
to pages/*.py, renderer.py, icons.py, or palette.py.

    python3 scripts/render_preview.py --page daily --mock-weather --output daily.png
    python3 scripts/render_preview.py --page hourly --mock-weather --output hourly.png
    python3 scripts/render_preview.py --config config.json --page daily --output daily.png
"""

import argparse
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from weather_station import fixtures, weather_client  # noqa: E402
from weather_station.config import load_config  # noqa: E402
from weather_station.renderer import RenderContext, render_page  # noqa: E402

PAGES = ("daily", "daily_secondary", "hourly")
DEFAULT_BUTTONS = {"A": "daily", "B": "daily_secondary", "D": "hourly"}


def main():
    parser = argparse.ArgumentParser(description="Render a weather-station page to PNG, no hardware")
    parser.add_argument("--config", default="config.json", help="path to config.json")
    parser.add_argument("--page", default="daily", choices=PAGES)
    parser.add_argument("--subpage", type=int, default=0)
    parser.add_argument("--output", default="preview.png")
    parser.add_argument(
        "--mock-weather", action="store_true",
        help="use a canned forecast fixture covering every icon category, no network call, no config file needed",
    )
    parser.add_argument(
        "--offline", action="store_true",
        help="render as if the last weather fetch failed, to eyeball the header's red wifi icon",
    )
    args = parser.parse_args()

    days = hours = updated_at = None
    button_map = DEFAULT_BUTTONS
    units = "fahrenheit"
    location_label = ""

    if args.mock_weather:
        days, hours = fixtures.MOCK_DAILY, fixtures.MOCK_HOURLY
        updated_at = int(time.time())
        if Path(args.config).exists():
            config = load_config(args.config)
            button_map = config.display.buttons
            units = config.units
    else:
        config = load_config(args.config)
        button_map = config.display.buttons
        units = config.units

        use_secondary = args.page == "daily_secondary"
        if use_secondary and not config.has_secondary_location:
            print("config has no secondary_latitude/secondary_longitude set", file=sys.stderr)
            raise SystemExit(1)
        latitude = config.secondary_latitude if use_secondary else config.latitude
        longitude = config.secondary_longitude if use_secondary else config.longitude
        cache_path = config.secondary_cache_path if use_secondary else config.cache_path
        location_label = config.secondary_label if use_secondary else config.primary_label

        try:
            days, hours = weather_client.fetch_forecast(
                latitude, longitude,
                config.units, config.forecast_days, config.forecast_hours,
            )
            updated_at = int(time.time())
        except weather_client.WeatherFetchError as exc:
            print(f"live weather fetch failed ({exc}), falling back to cache", file=sys.stderr)
            days, hours, updated_at = weather_client.load_cache(cache_path)

    ctx = RenderContext(
        page_name=args.page,
        subpage=args.subpage,
        button_page_map=button_map,
        daily=days,
        hourly=hours,
        weather_updated_at=updated_at,
        weather_fetch_ok=not args.offline,
        units=units,
        location_label=location_label,
    )
    image = render_page(args.page, ctx)
    image.save(args.output)
    print(f"wrote {args.output}  (page={args.page} subpage={args.subpage})")


if __name__ == "__main__":
    main()
