"""Physical button wiring (gpiozero) and the page-navigation state machine.

The state machine is a plain, dependency-free class deliberately kept
separate from GpioButtons so it's unit-testable by feeding it synthetic
ButtonEvents -- no GPIO, no gpiozero, no real hardware required.

BCM pin mapping for the Inky Impression's four rear buttons (confirmed
against Pimoroni's own example):
    A = GPIO5, B = GPIO6, C = GPIO16, D = GPIO24

Only A and B are mapped to pages for this device (7-day / hourly forecast);
C and D are wired but intentionally unmapped in config, so pressing them is
a harmless no-op (see PageStateMachine.handle_event below).
"""

import logging
import time
from dataclasses import dataclass

log = logging.getLogger("weather_station.buttons")

BUTTON_PINS = {"A": 5, "B": 6, "C": 16, "D": 24}


@dataclass
class ButtonEvent:
    button: str  # "A" | "B" | "C" | "D"
    pressed_at: float


class PageStateMachine:
    """Tracks which page is on screen and, for pages long enough to need
    pagination, which subpage.

    Pressing the button already mapped to the current page advances the
    subpage; pressing a different mapped button switches pages and resets
    to subpage 0. This class doesn't know how many subpages a page actually
    has -- callers (the page renderer) compute `subpage % total_subpages`
    themselves.
    """

    def __init__(self, button_page_map, default_page="daily"):
        self.button_page_map = dict(button_page_map)
        self.current_page = default_page
        self.subpage = 0

    def handle_event(self, event: ButtonEvent):
        page = self.button_page_map.get(event.button)
        if page is None:
            log.warning("button %s has no page mapping, ignoring", event.button)
            return False
        if page == self.current_page:
            self.subpage += 1
        else:
            self.current_page = page
            self.subpage = 0
        log.info(
            "button %s pressed -> page=%s subpage=%s", event.button, self.current_page, self.subpage,
        )
        return True


class GpioButtons:
    """Wires the four physical buttons to an asyncio.Queue of ButtonEvents.

    gpiozero's callbacks fire on its own internal thread, so events are
    handed to the asyncio loop via call_soon_threadsafe rather than pushed
    directly onto the queue.
    """

    def __init__(self, loop, event_queue, pins=None):
        # Imported lazily: gpiozero touches GPIO on construction of a
        # Button, which only makes sense on real hardware (or under its
        # own mock-pin-factory env var for local testing).
        from gpiozero import Button

        self._loop = loop
        self._queue = event_queue
        self._buttons = []
        for label, pin in (pins or BUTTON_PINS).items():
            btn = Button(pin, bounce_time=0.05)
            btn.when_pressed = self._make_handler(label, pin)
            self._buttons.append(btn)
        log.info("wired buttons: %s", pins or BUTTON_PINS)

    def _make_handler(self, label, pin):
        def _on_press():
            # Logged here, on gpiozero's own callback thread, rather than
            # only after the state machine processes the event -- this is
            # the earliest point that confirms the GPIO edge itself was
            # detected, independent of anything downstream (asyncio queue,
            # page mapping). If a press never logs this line, the problem
            # is physical/electrical (bad contact, wiring); if it logs here
            # but not "button X pressed -> page=..." in buttons.py, the
            # problem is downstream in the app.
            log.info("physical button %s pressed (GPIO%s)", label, pin)
            event = ButtonEvent(button=label, pressed_at=time.monotonic())
            self._loop.call_soon_threadsafe(self._queue.put_nowait, event)
        return _on_press

    def close(self):
        for btn in self._buttons:
            btn.close()
