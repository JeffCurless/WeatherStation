# Configuration reference

`config.json` is plain JSON (no comments, no YAML dependency) so it parses
with nothing beyond the Python stdlib. Copy `config.example.json` to
`config.json` (or wherever `--config`/`WEATHER_STATION_CONFIG` points) and
edit `latitude`/`longitude` for your location.

Read by `weather_station/config.py`.

| field | type | default | meaning |
|---|---|---|---|
| `latitude` | float | — (required) | Forecast location, passed straight to Open-Meteo. |
| `longitude` | float | — (required) | Forecast location, passed straight to Open-Meteo. |
| `units` | string | `"fahrenheit"` | `"fahrenheit"` or `"celsius"` -- Open-Meteo's `temperature_unit` param. |
| `forecast_days` | int | `7` | 1-16, how many days of daily forecast to request (button A). |
| `forecast_hours` | int | `10` | How many hourly readings to request, starting at the current local hour (button B). |
| `poll_interval_seconds` | int | `1800` | How often the display re-fetches the forecast from Open-Meteo. |
| `cache_path` | string | `"weather_cache.json"` | Path to the on-disk weather cache, read on startup so a restart shows last-known weather immediately instead of a blank page. Relative paths resolve against the process's working directory (under systemd, that's `WorkingDirectory` -- see `systemd/weather-station.service`). |
| `display.refresh_min_interval_seconds` | int | `90` | Minimum wall-clock gap between physical e-ink refreshes triggered by a new weather fetch (not button presses -- see below). Clamped up to at least 45s in code (`refresh_policy.HARD_MIN_REFRESH_SECONDS`) regardless of what's configured here -- the panel's confirmed ~21s refresh time needs a genuine idle gap between unattended background refreshes. |
| `display.buttons` | object | `{"A": "daily", "B": "hourly"}` | Maps physical buttons to page names (`daily`, `hourly`). `C` and `D` are intentionally omitted -- pressing them is a harmless no-op (logged at WARNING level) rather than a page switch. To use them later, add e.g. `"C": "somepage"` here plus a matching page module. |

**Button responsiveness.** A button press refreshes the display as soon as
nothing else is already mid-refresh -- it is not subject to
`display.refresh_min_interval_seconds`, which only throttles background
weather-fetch refreshes. See `refresh_policy.py` for why.

**Weather source.** Weather comes from [Open-Meteo](https://open-meteo.com/)
-- free, no API key, no signup, non-commercial use up to 10,000
requests/day. A single HTTPS GET requests both the daily forecast (button
A) and the hourly forecast (button B) together, so there's only one fetch
per `poll_interval_seconds`, not two.

**Local dev without a config file.** `scripts/render_preview.py
--mock-weather` doesn't require `config.json` to exist at all -- it uses a
canned fixture (`weather_station/fixtures.py`) covering every icon
category, for fast layout iteration with no network call.
