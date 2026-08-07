"""Real Inky Impression driver, or a headless mock for development.

`get_driver()` is the only thing main.py/scripts should call -- it decides
which implementation to hand back so nothing else in this package needs an
`if mock:` branch scattered through it.
"""

import logging
from pathlib import Path

log = logging.getLogger("weather_station.inky_driver")

DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
DISPLAY_RESOLUTION = (DISPLAY_WIDTH, DISPLAY_HEIGHT)


class MockInky:
    """Drop-in stand-in for a real `inky.auto.auto()` handle.

    Writes whatever image was set to a PNG instead of touching hardware.
    Deliberately does NOT import the real `inky` package anywhere in this
    class or module at import time -- that package probes for Pi-specific
    SPI/I2C/GPIO hardware on import and raises on any machine that isn't a
    Pi with the panel wired up, which would make this module (and therefore
    render_preview.py) unusable for local development.
    """

    resolution = DISPLAY_RESOLUTION
    width, height = DISPLAY_RESOLUTION

    def __init__(self, output_path="preview.png"):
        self.output_path = Path(output_path)
        self._image = None
        self.show_count = 0

    def set_image(self, image):
        self._image = image

    def show(self):
        if self._image is None:
            raise RuntimeError("set_image() must be called before show()")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._image.save(self.output_path)
        self.show_count += 1
        log.info("mock display: wrote %s (show #%d)", self.output_path, self.show_count)


def get_driver(mock_output_path=None):
    """Returns a real Inky Impression handle, or a MockInky if
    mock_output_path is given. The real `inky` import is deliberately local
    to this branch -- see MockInky's docstring."""
    if mock_output_path is not None:
        return MockInky(mock_output_path)

    try:
        from inky.auto import auto  # noqa: local import, probes hardware
    except ModuleNotFoundError as exc:
        # inky is installed into a dedicated --system-site-packages venv
        # (install.sh creates it at /opt/weather-station/venv), not system
        # Python -- PEP 668 refuses a bare `pip install` on current
        # Raspberry Pi OS. weather-station.service already points at that
        # venv's python3, but an ad-hoc script run with plain `python3` hits
        # exactly this. See docs/deployment.md.
        raise ModuleNotFoundError(
            "inky is not importable from this Python interpreter. It's installed "
            "into a dedicated venv, not system Python (see docs/deployment.md) -- "
            "run this script with that venv's interpreter instead, e.g.:\n"
            "  /opt/weather-station/venv/bin/python3 <this-script> ...\n"
            f"(original error: {exc})"
        ) from exc

    display = auto(ask_user=False, verbose=False)
    return display
