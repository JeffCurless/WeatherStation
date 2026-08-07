"""E Ink Spectra 6 palette constants.

The Inky Impression 7.3" panel only physically supports these six colors --
no grey, no arbitrary RGB, no gradients. Every page must draw exclusively
with these constants (flat fills and unantialiased text) so nothing
downstream ever needs to dither or quantize: what we draw is already exactly
what the panel can show.

These RGB values are the panel's *actual* ink approximations, taken directly
from Pimoroni's own driver for this chip
(`inky.inky_ac073tc1a.InkyAC073TC1A.SATURATED_PALETTE`) -- not naive pure RGB.
That matters: the real "green" ink is a dark, muted (3, 124, 76), not bright
(0, 255, 0). Using pure RGB here would make on-screen/PNG previews look
nothing like the physical panel and, worse, would make a naive
luminance-based text-color choice pick black text on green -- which is
nearly unreadable on the real ink, even though pure green is bright enough
for black text to read fine.
"""

BLACK = (0, 0, 0)
WHITE = (217, 242, 255)
RED = (245, 80, 34)
GREEN = (3, 124, 76)
BLUE = (27, 46, 198)
YELLOW = (255, 255, 68)

PALETTE = (BLACK, WHITE, RED, GREEN, BLUE, YELLOW)

BACKGROUND = WHITE
FOREGROUND = BLACK
GRID_LINE = BLACK

# Perceptual (Rec. 709) luminance, not a hand-picked "these ones are dark"
# set -- with the real ink RGB values above, some colors turn out darker
# than a naive glance at pure RGB would suggest.
_LUMINANCE_THRESHOLD = 128


def _luminance(rgb):
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def text_color_for(background):
    return WHITE if _luminance(background) < _LUMINANCE_THRESHOLD else BLACK
