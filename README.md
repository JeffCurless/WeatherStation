# weather-station

A standalone weather display for a Raspberry Pi (Zero W or Pi 4) driving a
[Pimoroni Inky Impression 7.3"](https://shop.pimoroni.com/products/inky-impression-7-3)
e-ink panel (800x480, 6-color Spectra), with 4 physical buttons.

- **Button A** (default): 7-day forecast, with extra detail for today
  (including sunrise/sunset times); each day's icon swaps to a moon for
  clear/partly-cloudy conditions after sunset.
- **Button B**: hour-by-hour forecast for the next 10 hours, including the
  current hour.
- **Buttons C/D**: reserved, unused for now.

Weather comes from [Open-Meteo](https://open-meteo.com/) -- free, no API
key, no signup, non-commercial use up to 10,000 requests/day.

## Quickstart (no hardware needed)

```
python3 -m venv .venv && source .venv/bin/activate
pip install pillow

# render a page to PNG using canned mock data -- no config file, no network
python3 scripts/render_preview.py --page daily --mock-weather --output daily.png
python3 scripts/render_preview.py --page hourly --mock-weather --output hourly.png

# or against the real Open-Meteo API
cp config/config.example.json config.json    # edit latitude/longitude
python3 scripts/render_preview.py --config config.json --page daily --output daily.png

# confirm the real API call works, without running the full app
python3 scripts/live_api_smoke_test.py --latitude 42.8285 --longitude -71.7105

# run the full app (writes to a PNG instead of real hardware, skips GPIO)
python3 weather_station/main.py --config config.json --mock-output preview.png
```

## Tests

```
python3 -m unittest discover -s tests
```

## Deploying to a Pi

See [`docs/deployment.md`](docs/deployment.md) for hardware setup (SPI,
buttons), `install.sh` usage, and systemd service details.

## Configuration

See [`config/README.md`](config/README.md) for the full field reference.

## Project layout

```
weather_station/       importable package: config, weather client, renderer, pages, main loop
scripts/                render_preview.py, render_color_swatch.py, live_api_smoke_test.py
config/                 config.example.json + field reference
systemd/                weather-station.service
docs/                   deployment.md
tests/                  unit tests (stdlib unittest, no network/hardware)
install.sh              systemd install script
```
