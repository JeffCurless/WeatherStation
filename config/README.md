# Configuration reference

`config.json` is plain JSON (no comments, no YAML dependency) so it parses
with nothing beyond the Python stdlib. Copy `config.example.json` to
`config.json` (or wherever `--config`/`WEATHER_STATION_CONFIG` points) and
edit `latitude`/`longitude` for your location.

Read by `weather_station/config.py`.

| field | type | default | meaning |
|---|---|---|---|
| `latitude` | float | — (required) | Primary forecast location, passed straight to Open-Meteo (button A, and button D when B/`daily_secondary` wasn't the last page checked). |
| `longitude` | float | — (required) | Primary forecast location, passed straight to Open-Meteo. |
| `secondary_latitude` | float | none | Secondary forecast location (button B). Must be set together with `secondary_longitude`, or left out entirely -- with neither set, button B's page just renders "forecast unavailable". |
| `secondary_longitude` | float | none | Secondary forecast location (button B). See `secondary_latitude`. |
| `secondary_label` | string | `"Secondary"` | Short label shown in the header (e.g. "7-Day Forecast — Queen's University Belfast") whenever the secondary location's data is on screen -- button B, or button D if B was the last location checked. |
| `primary_label` | string | `"Home"` | Same idea as `secondary_label` but for the primary location -- shown in the header (e.g. "7-Day Forecast — Home") whenever the primary location's data is on screen: button A, or button D if A was the last location checked. |
| `units` | string | `"fahrenheit"` | `"fahrenheit"` or `"celsius"` -- Open-Meteo's `temperature_unit` param. Applies to both locations. |
| `forecast_days` | int | `7` | 1-16, how many days of daily forecast to request (buttons A/B). |
| `forecast_hours` | int | `10` | How many hourly readings to request, starting at the current local hour (button D). |
| `poll_interval_seconds` | int | `1800` | How often the display re-fetches the forecast from Open-Meteo. One fetch per location per interval. |
| `cache_path` | string | `"weather_cache.json"` | Path to the primary location's on-disk weather cache, read on startup so a restart shows last-known weather immediately instead of a blank page. Relative paths resolve against the process's working directory (under systemd, that's `WorkingDirectory` -- see `systemd/weather-station.service`). |
| `secondary_cache_path` | string | `"weather_cache_secondary.json"` | Same as `cache_path`, for the secondary location. Only read/written when `secondary_latitude`/`secondary_longitude` are set. |
| `display.refresh_min_interval_seconds` | int | `90` | Minimum wall-clock gap between physical e-ink refreshes triggered by a new weather fetch (not button presses -- see below). Clamped up to at least 45s in code (`refresh_policy.HARD_MIN_REFRESH_SECONDS`) regardless of what's configured here -- the panel's confirmed ~21s refresh time needs a genuine idle gap between unattended background refreshes. |
| `display.buttons` | object | `{"A": "daily", "B": "daily_secondary", "D": "hourly"}` | Maps physical buttons to page names (`daily`, `daily_secondary`, `hourly`). `daily` and `daily_secondary` render the same 7-day layout, sourced from the primary and secondary location respectively; `hourly` renders the 10-hour table for whichever of those two locations was checked most recently. `C` is intentionally omitted -- pressing it is a harmless no-op (logged at WARNING level) rather than a page switch, reserved for a future feature. To use it later, add e.g. `"C": "somepage"` here plus a matching page module. |

**Button responsiveness.** A button press refreshes the display as soon as
nothing else is already mid-refresh -- it is not subject to
`display.refresh_min_interval_seconds`, which only throttles background
weather-fetch refreshes. See `refresh_policy.py` for why.

**Weather source.** Weather comes from [Open-Meteo](https://open-meteo.com/)
-- free, no API key, no signup, non-commercial use up to 10,000
requests/day. A single HTTPS GET per location requests both the daily
forecast (buttons A/B) and the hourly forecast (button D) together, so
there's only one fetch per location per `poll_interval_seconds` -- one fetch
total with no secondary location configured, two once it is.

**Local dev without a config file.** `scripts/render_preview.py
--mock-weather` doesn't require `config.json` to exist at all -- it uses a
canned fixture (`weather_station/fixtures.py`) covering every icon
category, for fast layout iteration with no network call.
