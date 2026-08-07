#!/usr/bin/env python3
"""One-shot real Open-Meteo call: confirms the combined daily+hourly query
still works and prints a summary, without running the full app.

    python3 scripts/live_api_smoke_test.py --latitude 42.8285 --longitude -71.7105

Exits non-zero (with the WeatherFetchError message) on any network/parse
failure. Useful to re-run any time Open-Meteo's response shape is
suspected to have changed, and to snapshot a real response into
tests/fixtures/open_meteo_response.json with --save-raw.
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from weather_station import weather_client  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--latitude", type=float, required=True)
    parser.add_argument("--longitude", type=float, required=True)
    parser.add_argument("--units", default="fahrenheit", choices=("fahrenheit", "celsius"))
    parser.add_argument("--forecast-days", type=int, default=7)
    parser.add_argument("--forecast-hours", type=int, default=10)
    parser.add_argument(
        "--save-raw", default=None,
        help="also write the raw JSON response to this path (e.g. tests/fixtures/open_meteo_response.json)",
    )
    args = parser.parse_args()

    try:
        days, hours = weather_client.fetch_forecast(
            args.latitude, args.longitude, args.units, args.forecast_days, args.forecast_hours,
        )
    except weather_client.WeatherFetchError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)

    print(f"daily: {len(days)} day(s)")
    print(f"  first: {days[0]}")
    print(f"  last:  {days[-1]}")
    print(f"hourly: {len(hours)} hour(s)")
    print(f"  first: {hours[0]}")
    print(f"  last:  {hours[-1]}")

    if args.save_raw:
        params = {
            "latitude": args.latitude,
            "longitude": args.longitude,
            "daily": weather_client.DAILY_VARS,
            "hourly": weather_client.HOURLY_VARS,
            "temperature_unit": args.units,
            "wind_speed_unit": weather_client.WIND_SPEED_UNIT_BY_TEMPERATURE_UNIT.get(args.units, "kmh"),
            "forecast_days": args.forecast_days,
            "forecast_hours": args.forecast_hours,
            "timezone": "auto",
        }
        url = f"{weather_client.API_URL}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=weather_client.REQUEST_TIMEOUT_SECONDS) as resp:
            raw = resp.read()
        Path(args.save_raw).parent.mkdir(parents=True, exist_ok=True)
        Path(args.save_raw).write_text(json.dumps(json.loads(raw), indent=2))
        print(f"saved raw response to {args.save_raw}")


if __name__ == "__main__":
    main()
