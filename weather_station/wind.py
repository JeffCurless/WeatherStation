"""Wind direction formatting shared by pages/daily.py and pages/hourly.py."""

COMPASS_POINTS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def compass_direction(degrees):
    index = int((degrees / 45) + 0.5) % 8
    return COMPASS_POINTS[index]
