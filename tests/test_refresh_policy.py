import unittest

from weather_station.refresh_policy import HARD_MIN_REFRESH_SECONDS, RefreshPolicy


class _FakeClock:
    def __init__(self, start=0.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class TestRefreshPolicy(unittest.TestCase):
    def test_initial_refresh_is_forced(self):
        clock = _FakeClock()
        policy = RefreshPolicy(clock=clock)
        self.assertTrue(policy.should_refresh())

    def test_not_dirty_after_record_refresh(self):
        clock = _FakeClock()
        policy = RefreshPolicy(clock=clock)
        policy.record_refresh()
        self.assertFalse(policy.should_refresh())

    def test_mark_dirty_makes_it_refreshable_again_after_min_gap(self):
        clock = _FakeClock()
        policy = RefreshPolicy(refresh_min_interval_seconds=100, clock=clock)
        policy.record_refresh()
        policy.mark_dirty()

        clock.advance(50)
        self.assertFalse(policy.should_refresh())  # gap not elapsed yet

        clock.advance(51)  # total 101s elapsed
        self.assertTrue(policy.should_refresh())

    def test_hard_floor_enforced_even_with_lower_configured_value(self):
        policy = RefreshPolicy(refresh_min_interval_seconds=5)
        self.assertEqual(policy.refresh_min_interval_seconds, HARD_MIN_REFRESH_SECONDS)

    def test_button_press_refreshes_immediately_regardless_of_idle_gap(self):
        """Button-triggered dirty state is exempt from
        refresh_min_interval_seconds entirely -- a press should be servable
        as soon as should_refresh is next polled, not gated by any elapsed-
        time floor. Only "nothing else already in flight" applies, which is
        guaranteed structurally by main.py's loop shape, not by this class."""
        clock = _FakeClock()
        policy = RefreshPolicy(refresh_min_interval_seconds=200, clock=clock)
        policy.record_refresh()
        policy.mark_dirty(button=True)

        self.assertTrue(policy.should_refresh())  # no wait at all

    def test_non_button_dirty_uses_idle_gap(self):
        clock = _FakeClock()
        policy = RefreshPolicy(refresh_min_interval_seconds=200, clock=clock)
        policy.record_refresh()
        policy.mark_dirty()

        clock.advance(46)
        self.assertFalse(policy.should_refresh())  # idle gap (200s) not elapsed

        clock.advance(155)  # total 201s elapsed
        self.assertTrue(policy.should_refresh())

    def test_button_urgency_persists_across_ticks_without_a_new_press(self):
        """Regression test: once any pending dirty state was caused by a
        button press, should_refresh must keep skipping the idle-gap check
        on later ticks even with no further button events -- not silently
        fall back to the long idle gap just because the tick that first
        called mark_dirty(button=True) has passed. Otherwise a press that
        arrives while should_refresh isn't being polled synchronously (e.g.
        mid-render) could be starved by the idle gap before main.py gets
        back around to checking again."""
        clock = _FakeClock()
        policy = RefreshPolicy(refresh_min_interval_seconds=200, clock=clock)
        policy.record_refresh()
        policy.mark_dirty(button=True)

        # Simulate a later tick with no new button event -- mark_dirty is
        # not called again, only should_refresh is polled, as main.py does.
        clock.advance(1)
        self.assertTrue(policy.should_refresh())

    def test_record_refresh_clears_button_urgency(self):
        clock = _FakeClock()
        policy = RefreshPolicy(refresh_min_interval_seconds=200, clock=clock)
        policy.record_refresh()
        policy.mark_dirty(button=True)
        policy.record_refresh()

        self.assertFalse(policy.should_refresh())

        policy.mark_dirty()  # a later, non-button dirty
        clock.advance(1)
        self.assertFalse(policy.should_refresh())  # back to the idle gap


if __name__ == "__main__":
    unittest.main()
