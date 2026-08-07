import json
import tempfile
import unittest
from pathlib import Path

from weather_station.config import ConfigError, load_config


class TestLoadConfig(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.path = Path(self._tmpdir.name) / "config.json"

    def _write(self, data):
        self.path.write_text(json.dumps(data))

    def test_happy_path(self):
        self._write({
            "latitude": 42.8285,
            "longitude": -71.7105,
            "units": "celsius",
            "forecast_days": 5,
            "forecast_hours": 6,
            "poll_interval_seconds": 900,
            "cache_path": "custom_cache.json",
            "display": {
                "refresh_min_interval_seconds": 120,
                "buttons": {"A": "daily", "B": "hourly", "C": "extra"},
            },
        })
        config = load_config(self.path)
        self.assertEqual(config.latitude, 42.8285)
        self.assertEqual(config.longitude, -71.7105)
        self.assertEqual(config.units, "celsius")
        self.assertEqual(config.forecast_days, 5)
        self.assertEqual(config.forecast_hours, 6)
        self.assertEqual(config.poll_interval_seconds, 900)
        self.assertEqual(config.cache_path, "custom_cache.json")
        self.assertEqual(config.display.refresh_min_interval_seconds, 120)
        self.assertEqual(config.display.buttons, {"A": "daily", "B": "hourly", "C": "extra"})

    def test_defaults_applied_when_omitted(self):
        self._write({"latitude": 42.8285, "longitude": -71.7105})
        config = load_config(self.path)
        self.assertEqual(config.units, "fahrenheit")
        self.assertEqual(config.forecast_days, 7)
        self.assertEqual(config.forecast_hours, 10)
        self.assertEqual(config.poll_interval_seconds, 1800)
        self.assertEqual(config.cache_path, "weather_cache.json")
        self.assertEqual(config.display.refresh_min_interval_seconds, 90)
        self.assertEqual(config.display.buttons, {"A": "daily", "B": "hourly"})

    def test_missing_latitude_raises(self):
        self._write({"longitude": -71.7105})
        with self.assertRaises(ConfigError):
            load_config(self.path)

    def test_missing_longitude_raises(self):
        self._write({"latitude": 42.8285})
        with self.assertRaises(ConfigError):
            load_config(self.path)

    def test_missing_file_raises(self):
        with self.assertRaises(ConfigError):
            load_config(Path(self._tmpdir.name) / "does_not_exist.json")

    def test_malformed_json_raises(self):
        self.path.write_text("{not valid json")
        with self.assertRaises(ConfigError):
            load_config(self.path)

    def test_invalid_units_raises(self):
        self._write({"latitude": 42.8285, "longitude": -71.7105, "units": "kelvin"})
        with self.assertRaises(ConfigError):
            load_config(self.path)

    def test_forecast_days_out_of_range_raises(self):
        self._write({"latitude": 42.8285, "longitude": -71.7105, "forecast_days": 17})
        with self.assertRaises(ConfigError):
            load_config(self.path)


if __name__ == "__main__":
    unittest.main()
