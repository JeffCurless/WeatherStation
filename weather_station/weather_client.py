"""Fetches a combined daily+hourly forecast from Open-Meteo (open-meteo.com)
-- free, no API key, no signup, non-commercial use. stdlib-only HTTP: a
single HTTPS GET via urllib.request, parsed with json.

Results are cached to a JSON file (read/write via atomic temp-file +
os.replace) so a process restart has last-known weather immediately instead
of a blank page until the next fetch.
"""

import json
import logging
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

log = logging.getLogger("weather_station.weather_client")

API_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 10

DAILY_VARS = (
    "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,"
    "wind_speed_10m_max,wind_direction_10m_dominant,uv_index_max"
)
HOURLY_VARS = "temperature_2m,weather_code,precipitation_probability,wind_speed_10m,wind_direction_10m,uv_index"

# Open-Meteo has no "imperial/metric" toggle for wind -- it's a standalone
# unit param. Tied to temperature_unit here so a "fahrenheit" config reads
# mph throughout (matching US expectations) and "celsius" reads km/h.
WIND_SPEED_UNIT_BY_TEMPERATURE_UNIT = {"fahrenheit": "mph", "celsius": "kmh"}


class WeatherFetchError(Exception):
    pass


def fetch_forecast(latitude, longitude, units="fahrenheit", forecast_days=7, forecast_hours=10):
    """Returns (days, hours).

    days:  list of {"date": "2026-08-04", "hi": 82.8, "lo": 60.1,
                     "weather_code": 2, "precip_probability": 0,
                     "wind_speed": 12.4, "wind_direction": 270,
                     "uv_index": 6.0}
    hours: list of {"time": "2026-08-04T19:00", "temperature": 78.0,
                     "weather_code": 0, "precip_probability": 0,
                     "wind_speed": 8.1, "wind_direction": 270, "uv_index": 0.0}
           "time" is the raw ISO string from Open-Meteo, starting at the
           current local hour (not midnight) when forecast_hours + timezone
           =auto are both set, as requested here -- formatting for display
           is the page's job, not this client's.

    Raises WeatherFetchError on any network/parse failure in EITHER block --
    treated as one atomic fetch so callers don't have to reason about
    partial success (both pages fall back to cache together)."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": DAILY_VARS,
        "hourly": HOURLY_VARS,
        "temperature_unit": units,
        "wind_speed_unit": WIND_SPEED_UNIT_BY_TEMPERATURE_UNIT.get(units, "kmh"),
        "forecast_days": forecast_days,
        "forecast_hours": forecast_hours,
        "timezone": "auto",
    }
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    log.debug("requesting %s", url)
    try:
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            raw = resp.read()
            log.debug("weather response: status=%s bytes=%d", resp.status, len(raw))
            data = json.loads(raw)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise WeatherFetchError(f"request failed: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise WeatherFetchError(f"invalid json in response: {exc}") from exc

    try:
        daily = data["daily"]
        days = []
        for i, date in enumerate(daily["time"]):
            days.append({
                "date": date,
                "hi": daily["temperature_2m_max"][i],
                "lo": daily["temperature_2m_min"][i],
                "weather_code": daily["weather_code"][i],
                "precip_probability": daily["precipitation_probability_max"][i],
                "wind_speed": daily["wind_speed_10m_max"][i],
                "wind_direction": daily["wind_direction_10m_dominant"][i],
                "uv_index": daily["uv_index_max"][i],
            })

        hourly = data["hourly"]
        hours = []
        for i, hour_time in enumerate(hourly["time"]):
            hours.append({
                "time": hour_time,
                "temperature": hourly["temperature_2m"][i],
                "weather_code": hourly["weather_code"][i],
                "precip_probability": hourly["precipitation_probability"][i],
                "wind_speed": hourly["wind_speed_10m"][i],
                "wind_direction": hourly["wind_direction_10m"][i],
                "uv_index": hourly["uv_index"][i],
            })
    except (KeyError, IndexError) as exc:
        raise WeatherFetchError(f"unexpected response shape: {exc}") from exc

    return days, hours


def load_cache(cache_path):
    """Returns (days, hours, fetched_at) from the cache file, or
    (None, None, None) if it doesn't exist or is unreadable."""
    try:
        raw = json.loads(Path(cache_path).read_text())
        return raw["days"], raw["hours"], raw["fetched_at"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError, OSError):
        return None, None, None


def save_cache(cache_path, days, hours, fetched_at=None):
    """Atomic write (temp file + os.replace) so a concurrent read from the
    display's own next poll never sees a half-written file."""
    fetched_at = int(fetched_at if fetched_at is not None else time.time())
    payload = json.dumps({"days": days, "hours": hours, "fetched_at": fetched_at})

    dir_name = os.path.dirname(cache_path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix=".weather_cache.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(payload)
        os.replace(tmp_path, cache_path)
    except OSError:
        log.exception("failed to write weather cache to %s", cache_path)
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
