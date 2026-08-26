import unittest

from weather_station.icons import category_for


class TestCategoryFor(unittest.TestCase):
    def test_daytime_defaults_unchanged(self):
        self.assertEqual(category_for(0), "clear")
        self.assertEqual(category_for(1), "partly_cloudy")
        self.assertEqual(category_for(3), "cloudy")

    def test_night_swaps_sun_bearing_categories_for_moon_variants(self):
        self.assertEqual(category_for(0, is_day=False), "clear_night")
        self.assertEqual(category_for(2, is_day=False), "partly_cloudy_night")

    def test_night_leaves_non_sun_categories_unchanged(self):
        self.assertEqual(category_for(3, is_day=False), "cloudy")
        self.assertEqual(category_for(63, is_day=False), "rain")
        self.assertEqual(category_for(96, is_day=False), "storm")


if __name__ == "__main__":
    unittest.main()
