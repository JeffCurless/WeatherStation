"""Load and validate config.json. See config/README.md for the field reference."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

VALID_UNITS = ("fahrenheit", "celsius")
MIN_FORECAST_DAYS = 1
MAX_FORECAST_DAYS = 16


class ConfigError(ValueError):
    pass


@dataclass
class DisplayConfig:
    refresh_min_interval_seconds: int = 90
    buttons: Dict[str, str] = field(default_factory=lambda: {"A": "daily", "B": "hourly"})


@dataclass
class WeatherStationConfig:
    latitude: float
    longitude: float
    units: str = "fahrenheit"
    forecast_days: int = 7
    forecast_hours: int = 10
    poll_interval_seconds: int = 1800
    cache_path: str = "weather_cache.json"
    display: DisplayConfig = field(default_factory=DisplayConfig)


def load_config(path) -> WeatherStationConfig:
    raw_path = Path(path)
    try:
        data = json.loads(raw_path.read_text())
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {raw_path}")
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid json in {raw_path}: {exc}") from exc

    if data.get("latitude") is None or data.get("longitude") is None:
        raise ConfigError("config must set 'latitude' and 'longitude'")

    units = data.get("units", "fahrenheit")
    if units not in VALID_UNITS:
        raise ConfigError(f"units must be one of {VALID_UNITS}, got {units!r}")

    forecast_days = data.get("forecast_days", 7)
    if not (MIN_FORECAST_DAYS <= forecast_days <= MAX_FORECAST_DAYS):
        raise ConfigError(
            f"forecast_days must be between {MIN_FORECAST_DAYS} and {MAX_FORECAST_DAYS}, got {forecast_days}"
        )

    display_data = data.get("display", {})
    display = DisplayConfig(
        refresh_min_interval_seconds=display_data.get("refresh_min_interval_seconds", 90),
        buttons=display_data.get("buttons", {"A": "daily", "B": "hourly"}),
    )

    return WeatherStationConfig(
        latitude=data["latitude"],
        longitude=data["longitude"],
        units=units,
        forecast_days=forecast_days,
        forecast_hours=data.get("forecast_hours", 10),
        poll_interval_seconds=data.get("poll_interval_seconds", 1800),
        cache_path=data.get("cache_path", "weather_cache.json"),
        display=display,
    )
