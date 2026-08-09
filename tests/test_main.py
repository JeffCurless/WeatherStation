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
        self.weather_state = {"days": None, "hours": None, "updated_at": None, "fetch_ok": True}

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


if __name__ == "__main__":
    unittest.main()
