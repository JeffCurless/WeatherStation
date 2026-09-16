import unittest

from weather_station.buttons import ButtonEvent, PageStateMachine


class TestPageStateMachine(unittest.TestCase):
    def setUp(self):
        self.psm = PageStateMachine({"A": "daily", "B": "hourly"}, default_page="daily")

    def test_starts_on_default_page(self):
        self.assertEqual(self.psm.current_page, "daily")
        self.assertEqual(self.psm.subpage, 0)

    def test_pressing_different_mapped_button_switches_page(self):
        result = self.psm.handle_event(ButtonEvent(button="B", pressed_at=0.0))
        self.assertTrue(result)
        self.assertEqual(self.psm.current_page, "hourly")
        self.assertEqual(self.psm.subpage, 0)

    def test_pressing_same_page_button_again_increments_subpage(self):
        self.psm.handle_event(ButtonEvent(button="A", pressed_at=0.0))
        self.assertEqual(self.psm.subpage, 1)
        self.psm.handle_event(ButtonEvent(button="A", pressed_at=0.0))
        self.assertEqual(self.psm.subpage, 2)
        self.assertEqual(self.psm.current_page, "daily")

    def test_switching_page_resets_subpage(self):
        self.psm.handle_event(ButtonEvent(button="A", pressed_at=0.0))
        self.assertEqual(self.psm.subpage, 1)
        self.psm.handle_event(ButtonEvent(button="B", pressed_at=0.0))
        self.assertEqual(self.psm.current_page, "hourly")
        self.assertEqual(self.psm.subpage, 0)

    def test_unmapped_button_is_a_noop(self):
        result = self.psm.handle_event(ButtonEvent(button="C", pressed_at=0.0))
        self.assertFalse(result)
        self.assertEqual(self.psm.current_page, "daily")
        self.assertEqual(self.psm.subpage, 0)

    def test_unmapped_d_button_is_a_noop(self):
        result = self.psm.handle_event(ButtonEvent(button="D", pressed_at=0.0))
        self.assertFalse(result)
        self.assertEqual(self.psm.current_page, "daily")


class TestPageStateMachineLocation(unittest.TestCase):
    """A/B (daily / daily_secondary) select a location; D (hourly) inherits
    whichever location was checked most recently, per README's button D
    spec ("shows the 10 hours from the last location checked")."""

    def setUp(self):
        self.psm = PageStateMachine(
            {"A": "daily", "B": "daily_secondary", "D": "hourly"}, default_page="daily",
        )

    def test_starts_on_primary_location(self):
        self.assertEqual(self.psm.location, "primary")

    def test_pressing_b_switches_to_secondary_location(self):
        self.psm.handle_event(ButtonEvent(button="B", pressed_at=0.0))
        self.assertEqual(self.psm.current_page, "daily_secondary")
        self.assertEqual(self.psm.location, "secondary")

    def test_pressing_d_keeps_last_checked_location(self):
        self.psm.handle_event(ButtonEvent(button="B", pressed_at=0.0))
        self.psm.handle_event(ButtonEvent(button="D", pressed_at=0.0))
        self.assertEqual(self.psm.current_page, "hourly")
        self.assertEqual(self.psm.location, "secondary")

    def test_pressing_d_then_a_then_d_again_follows_last_checked_location(self):
        self.psm.handle_event(ButtonEvent(button="B", pressed_at=0.0))
        self.psm.handle_event(ButtonEvent(button="D", pressed_at=0.0))
        self.assertEqual(self.psm.location, "secondary")

        self.psm.handle_event(ButtonEvent(button="A", pressed_at=0.0))
        self.assertEqual(self.psm.location, "primary")

        self.psm.handle_event(ButtonEvent(button="D", pressed_at=0.0))
        self.assertEqual(self.psm.current_page, "hourly")
        self.assertEqual(self.psm.location, "primary")

    def test_unmapped_c_button_does_not_change_location(self):
        self.psm.handle_event(ButtonEvent(button="B", pressed_at=0.0))
        self.psm.handle_event(ButtonEvent(button="C", pressed_at=0.0))
        self.assertEqual(self.psm.location, "secondary")


if __name__ == "__main__":
    unittest.main()
