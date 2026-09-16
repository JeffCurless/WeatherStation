import tempfile
import unittest
from pathlib import Path
from unittest import mock

from weather_station import main
from weather_station.config import WeatherStationConfig
from weather_station.weather_client import WeatherFetchError

_DAY = {"date": "2026-08-08", "hi": 80, "lo": 60, "weather_code": 0, "precip_probability": 0}
_HOUR = {"time": "2026-08-08T20:00", "temperature": 78.0, "weather_code": 0, "precip_probability": 0, "humidity": 50}


class TestRefreshWeatherFetchOkTransitions(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.config = WeatherStationConfig(
            latitude=42.8285, longitude=-71.7105,
            cache_path=str(Path(self._tmpdir.name) / "weather_cache.json"),
        )
        self.weather_state = {
            "primary": {"days": None, "hours": None},
            "secondary": {"days": None, "hours": None},
            "updated_at": None,
            "fetch_ok": True,
        }

    async def _refresh(self):
        import asyncio
        return await main._refresh_weather(asyncio.get_running_loop(), self.config, self.weather_state)

    async def test_first_failure_marks_dirty_and_flips_fetch_ok_false(self):
        with mock.patch("weather_station.weather_client.fetch_forecast", side_effect=WeatherFetchError("boom")):
            dirty = await self._refresh()

        self.assertTrue(dirty)
        self.assertFalse(self.weather_state["fetch_ok"])

    async def test_repeated_failure_does_not_remark_dirty(self):
        with mock.patch("weather_station.weather_client.fetch_forecast", side_effect=WeatherFetchError("boom")):
            await self._refresh()
            dirty = await self._refresh()

        self.assertFalse(dirty)
        self.assertFalse(self.weather_state["fetch_ok"])

    async def test_success_after_failure_marks_dirty_and_restores_fetch_ok(self):
        with mock.patch("weather_station.weather_client.fetch_forecast", side_effect=WeatherFetchError("boom")):
            await self._refresh()

        with mock.patch("weather_station.weather_client.fetch_forecast", return_value=([_DAY], [_HOUR])):
            dirty = await self._refresh()

        self.assertTrue(dirty)
        self.assertTrue(self.weather_state["fetch_ok"])

    async def test_success_always_marks_dirty_even_without_a_prior_failure(self):
        with mock.patch("weather_station.weather_client.fetch_forecast", return_value=([_DAY], [_HOUR])):
            dirty = await self._refresh()

        self.assertTrue(dirty)
        self.assertTrue(self.weather_state["fetch_ok"])
        self.assertEqual(self.weather_state["primary"], {"days": [_DAY], "hours": [_HOUR]})
        self.assertEqual(self.weather_state["secondary"], {"days": None, "hours": None})

    async def test_no_secondary_location_configured_does_not_fetch_secondary(self):
        with mock.patch(
            "weather_station.weather_client.fetch_forecast", return_value=([_DAY], [_HOUR])
        ) as fetch:
            await self._refresh()

        fetch.assert_called_once_with(
            self.config.latitude, self.config.longitude,
            self.config.units, self.config.forecast_days, self.config.forecast_hours,
        )


class TestRefreshWeatherSecondaryLocation(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        # Queen's University Belfast -- used for testing the secondary-location feature.
        self.config = WeatherStationConfig(
            latitude=42.8285, longitude=-71.7105,
            secondary_latitude=54.5840, secondary_longitude=-5.9346,
            cache_path=str(Path(self._tmpdir.name) / "weather_cache.json"),
            secondary_cache_path=str(Path(self._tmpdir.name) / "weather_cache_secondary.json"),
        )
        self.weather_state = {
            "primary": {"days": None, "hours": None},
            "secondary": {"days": None, "hours": None},
            "updated_at": None,
            "fetch_ok": True,
        }

    async def _refresh(self):
        import asyncio
        return await main._refresh_weather(asyncio.get_running_loop(), self.config, self.weather_state)

    async def test_fetches_and_stores_both_locations(self):
        secondary_day = {**_DAY, "date": "2026-08-09"}
        secondary_hour = {**_HOUR, "time": "2026-08-09T20:00"}
        with mock.patch(
            "weather_station.weather_client.fetch_forecast",
            side_effect=[([_DAY], [_HOUR]), ([secondary_day], [secondary_hour])],
        ) as fetch:
            dirty = await self._refresh()

        self.assertTrue(dirty)
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(self.weather_state["primary"], {"days": [_DAY], "hours": [_HOUR]})
        self.assertEqual(
            self.weather_state["secondary"], {"days": [secondary_day], "hours": [secondary_hour]}
        )

    async def test_secondary_fetch_failure_fails_the_whole_refresh(self):
        with mock.patch(
            "weather_station.weather_client.fetch_forecast",
            side_effect=[([_DAY], [_HOUR]), WeatherFetchError("boom")],
        ):
            dirty = await self._refresh()

        self.assertTrue(dirty)
        self.assertFalse(self.weather_state["fetch_ok"])
        # Atomic: primary's in-memory state isn't updated either, so both
        # locations fall back to cache together rather than going half-stale.
        self.assertEqual(self.weather_state["primary"], {"days": None, "hours": None})


if __name__ == "__main__":
    unittest.main()
