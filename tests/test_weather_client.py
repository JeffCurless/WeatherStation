import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from weather_station import weather_client

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "open_meteo_response.json"


class _FakeResponse:
    """Minimal stand-in for the urllib.request.urlopen context manager."""

    def __init__(self, raw_bytes, status=200):
        self._raw = raw_bytes
        self.status = status

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class TestFetchForecast(unittest.TestCase):
    def test_parses_real_captured_response(self):
        raw = FIXTURE_PATH.read_bytes()
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(raw)):
            days, hours = weather_client.fetch_forecast(42.8285, -71.7105)

        self.assertEqual(len(days), 7)
        self.assertEqual(len(hours), 10)

        first_day = days[0]
        self.assertEqual(
            set(first_day),
            {"date", "hi", "lo", "weather_code", "precip_probability", "wind_speed", "wind_direction", "uv_index"},
        )

        first_hour = hours[0]
        self.assertEqual(
            set(first_hour),
            {"time", "temperature", "weather_code", "precip_probability", "wind_speed", "wind_direction", "uv_index"},
        )
        self.assertEqual(first_hour["time"], "2026-08-04T20:00")

    def test_missing_daily_block_raises(self):
        raw = json.dumps({"hourly": {"time": [], "temperature_2m": [], "weather_code": [], "precipitation_probability": []}}).encode()
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(raw)):
            with self.assertRaises(weather_client.WeatherFetchError):
                weather_client.fetch_forecast(42.8285, -71.7105)

    def test_missing_hourly_block_raises(self):
        raw = json.dumps({"daily": {
            "time": ["2026-08-04"],
            "temperature_2m_max": [80],
            "temperature_2m_min": [60],
            "weather_code": [0],
            "precipitation_probability_max": [0],
        }}).encode()
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(raw)):
            with self.assertRaises(weather_client.WeatherFetchError):
                weather_client.fetch_forecast(42.8285, -71.7105)

    def test_malformed_json_raises(self):
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(b"not json")):
            with self.assertRaises(weather_client.WeatherFetchError):
                weather_client.fetch_forecast(42.8285, -71.7105)


class TestCache(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.cache_path = str(Path(self._tmpdir.name) / "weather_cache.json")

    def test_round_trip(self):
        days = [{"date": "2026-08-04", "hi": 80, "lo": 60, "weather_code": 0, "precip_probability": 0}]
        hours = [{"time": "2026-08-04T19:00", "temperature": 78.0, "weather_code": 0, "precip_probability": 0}]
        weather_client.save_cache(self.cache_path, days, hours, fetched_at=1700000000)

        loaded_days, loaded_hours, fetched_at = weather_client.load_cache(self.cache_path)
        self.assertEqual(loaded_days, days)
        self.assertEqual(loaded_hours, hours)
        self.assertEqual(fetched_at, 1700000000)

    def test_missing_file_returns_none_triple(self):
        days, hours, fetched_at = weather_client.load_cache(self.cache_path)
        self.assertIsNone(days)
        self.assertIsNone(hours)
        self.assertIsNone(fetched_at)


if __name__ == "__main__":
    unittest.main()
