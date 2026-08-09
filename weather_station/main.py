#!/usr/bin/env python3
"""weather-station entrypoint: owns the Inky panel and the four buttons.

Single-process asyncio loop -- no SQLite, no separate monitor process. The
only two things that ever mark the display dirty are a new successful
weather fetch (on config.poll_interval_seconds, default 30 min) and a
button press that changes the current page/subpage. A failed fetch just
leaves the last-known (possibly cached) forecast on screen.
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from weather_station.buttons import GpioButtons, PageStateMachine  # noqa: E402
from weather_station import inky_driver  # noqa: E402
from weather_station import weather_client  # noqa: E402
from weather_station.config import ConfigError, load_config  # noqa: E402
from weather_station.refresh_policy import RefreshPolicy  # noqa: E402
from weather_station.renderer import RenderContext, render_page  # noqa: E402

log = logging.getLogger("weather_station.main")


def build_context(config, page_state, weather_state):
    return RenderContext(
        page_name=page_state.current_page,
        subpage=page_state.subpage,
        button_page_map=config.display.buttons,
        daily=weather_state["days"],
        hourly=weather_state["hours"],
        weather_updated_at=weather_state["updated_at"],
        weather_fetch_ok=weather_state["fetch_ok"],
        units=config.units,
    )


async def render_and_show(driver, config, page_state, weather_state, loop):
    ctx = build_context(config, page_state, weather_state)
    image = render_page(ctx.page_name, ctx)
    driver.set_image(image)
    await loop.run_in_executor(None, driver.show)
    log.info("refreshed display: page=%s subpage=%s", ctx.page_name, ctx.subpage)
    return ctx


async def _refresh_weather(loop, config, weather_state):
    """Runs the blocking HTTPS fetch off the event loop and, on success,
    updates weather_state in place and mirrors it to the on-disk cache.
    Returns True if the display should be marked dirty: always on a
    successful fetch (new data, and clears the offline icon if it was
    showing), or on a failed fetch only the moment it *becomes* the first
    consecutive failure (so a still-offline device doesn't force a redraw
    every single poll_interval_seconds -- the icon appeared once, it stays
    until connectivity actually returns)."""
    log.debug(
        "weather fetch starting: lat=%s lon=%s units=%s forecast_days=%s forecast_hours=%s",
        config.latitude, config.longitude, config.units,
        config.forecast_days, config.forecast_hours,
    )
    try:
        days, hours = await loop.run_in_executor(
            None, weather_client.fetch_forecast,
            config.latitude, config.longitude,
            config.units, config.forecast_days, config.forecast_hours,
        )
    except weather_client.WeatherFetchError:
        log.exception("weather fetch failed; keeping last-known forecast")
        was_ok = weather_state["fetch_ok"]
        weather_state["fetch_ok"] = False
        return was_ok

    now = int(time.time())
    weather_state["days"] = days
    weather_state["hours"] = hours
    weather_state["updated_at"] = now
    weather_state["fetch_ok"] = True
    await loop.run_in_executor(None, weather_client.save_cache, config.cache_path, days, hours, now)
    log.info("weather updated: %d day(s), %d hour(s)", len(days), len(hours))
    return True


async def main_async(config_path, mock_output_path=None):
    config = load_config(config_path)

    driver = inky_driver.get_driver(mock_output_path)
    refresh_policy = RefreshPolicy(
        refresh_min_interval_seconds=config.display.refresh_min_interval_seconds,
    )
    page_state = PageStateMachine(config.display.buttons)

    weather_state = {"days": None, "hours": None, "updated_at": None, "fetch_ok": True}
    cached_days, cached_hours, cached_at = weather_client.load_cache(config.cache_path)
    weather_state["days"] = cached_days
    weather_state["hours"] = cached_hours
    weather_state["updated_at"] = cached_at

    loop = asyncio.get_running_loop()
    button_queue = asyncio.Queue()
    gpio_buttons = None
    if mock_output_path is None:
        try:
            gpio_buttons = GpioButtons(loop, button_queue)
        except Exception:
            log.exception("could not initialize GPIO buttons; continuing without physical input")

    stop_event = asyncio.Event()
    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                pass  # e.g. platforms without asyncio signal support

    log.info(
        "weather-station starting: cache=%s mock=%s lat=%s lon=%s "
        "poll_interval_seconds=%s cached_days=%s cached_hours=%s cached_at=%s",
        config.cache_path, mock_output_path is not None, config.latitude, config.longitude,
        config.poll_interval_seconds,
        len(cached_days) if cached_days else 0,
        len(cached_hours) if cached_hours else 0,
        cached_at,
    )

    last_weather_fetch = 0.0
    try:
        while not stop_event.is_set():
            while not button_queue.empty():
                event = button_queue.get_nowait()
                if page_state.handle_event(event):
                    refresh_policy.mark_dirty(button=True)

            now = loop.time()
            if now - last_weather_fetch >= config.poll_interval_seconds:
                last_weather_fetch = now
                if await _refresh_weather(loop, config, weather_state):
                    refresh_policy.mark_dirty()

            if refresh_policy.should_refresh():
                await render_and_show(driver, config, page_state, weather_state, loop)
                refresh_policy.record_refresh()

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
    finally:
        log.info("shutting down")
        if gpio_buttons is not None:
            gpio_buttons.close()


def main():
    parser = argparse.ArgumentParser(description="weather-station: Inky Impression renderer")
    parser.add_argument(
        "--config",
        default=os.environ.get("WEATHER_STATION_CONFIG", "config.json"),
        help="path to config.json (default: %(default)s)",
    )
    parser.add_argument(
        "--mock-output",
        default=None,
        help="write to this PNG path instead of driving real Inky hardware "
             "(skips GPIO button init too -- for development off-Pi)",
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        asyncio.run(main_async(args.config, args.mock_output))
    except ConfigError as exc:
        log.error("config error: %s", exc)
        raise SystemExit(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
