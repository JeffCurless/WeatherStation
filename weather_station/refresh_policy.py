"""Coalesces state changes into infrequent physical e-ink refreshes.

The Inky Impression 7.3" panel takes roughly 20-35 seconds for a full
refresh (confirmed ~21s on-device) and has no fast partial-refresh mode, so
pushing a new image on every background weather poll would be both slow and
visually distracting. This module decides *when* a background refresh is
actually warranted; main.py just calls should_refresh() before invoking the
driver's blocking show().

Button presses are deliberately exempt from that idle-gap throttle -- a
press means someone is standing at the panel waiting for a response, so it
refreshes as soon as nothing else is already in flight. main.py's main loop
is a single coroutine that always awaits render_and_show() to completion
before calling should_refresh() again, so "nothing already in flight" is
structurally guaranteed by that loop shape -- RefreshPolicy doesn't need its
own "refresh in progress" flag to enforce it.

Unlike a device that also has to detect independent background state
changes, this device's only two dirty triggers are a new successful weather
fetch and a button-driven page/subpage change -- both call mark_dirty()
directly, so there's no separate state-hash/diff step needed here.
"""

import time

# Hard floor on how often a *background* (non-button) refresh can repeat --
# confirmed on-device refresh time is ~21s, and we want a genuine idle gap
# between unattended weather-poll refreshes, not back-to-back ones. Does not
# apply to button-triggered refreshes; see module docstring.
HARD_MIN_REFRESH_SECONDS = 45


class RefreshPolicy:
    def __init__(self, refresh_min_interval_seconds=90, clock=time.monotonic):
        self.refresh_min_interval_seconds = max(refresh_min_interval_seconds, HARD_MIN_REFRESH_SECONDS)
        self._clock = clock
        self._dirty = True  # force an initial refresh on startup
        self._dirty_from_button = True
        self._last_refresh_at = None

    def mark_dirty(self, button=False):
        """Force-dirty, e.g. on a new weather fetch or a button press that
        changed the page.

        `button` records *why* -- once any pending dirty state was caused by
        a button press, should_refresh keeps skipping the idle-gap check on
        every subsequent tick until it's actually serviced, even if later
        ticks have no button event of their own. Without this, a button
        press that lands mid-idle-gap would fall back to waiting out the
        remainder of that gap on the very next tick, and a second press
        arriving before it elapsed would silently overwrite the first
        press's page/subpage before it was ever drawn.
        """
        self._dirty = True
        if button:
            self._dirty_from_button = True

    @property
    def dirty(self):
        return self._dirty

    def should_refresh(self):
        if not self._dirty:
            return False
        if self._dirty_from_button:
            return True
        if self._last_refresh_at is None:
            return True
        elapsed = self._clock() - self._last_refresh_at
        return elapsed >= self.refresh_min_interval_seconds

    def record_refresh(self):
        self._last_refresh_at = self._clock()
        self._dirty = False
        self._dirty_from_button = False
