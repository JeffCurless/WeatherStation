"""Canned daily+hourly weather data for offline layout iteration and tests
-- no network call needed. Deliberately spans every icon category
(clear/partly_cloudy/cloudy/fog/rain/snow/storm) and a spread of
precipitation probabilities (some above, some below hourly.py's
RAIN_TICK_THRESHOLD) so a single render exercises every visual branch. The
first hourly entry is after sunset (is_day=False, weather_code=clear) so a
render also exercises the night/moon icon on the "Today" tile by default.
"""

# WMO weather codes: 0=clear, 2=partly cloudy, 3=cloudy, 45=fog, 63=rain,
# 73=snow, 96=storm.
MOCK_DAILY = [
    {"date": "2026-08-04", "hi": 82, "lo": 60, "weather_code": 0, "precip_probability": 0, "wind_speed": 6, "wind_direction": 180, "uv_index": 8.0, "sunrise": "2026-08-04T05:52", "sunset": "2026-08-04T20:05"},
    {"date": "2026-08-05", "hi": 80, "lo": 58, "weather_code": 2, "precip_probability": 10, "wind_speed": 9, "wind_direction": 225, "uv_index": 6.0, "sunrise": "2026-08-05T05:53", "sunset": "2026-08-05T20:04"},
    {"date": "2026-08-06", "hi": 75, "lo": 55, "weather_code": 3, "precip_probability": 20, "wind_speed": 12, "wind_direction": 270, "uv_index": 4.0, "sunrise": "2026-08-06T05:54", "sunset": "2026-08-06T20:02"},
    {"date": "2026-08-07", "hi": 68, "lo": 50, "weather_code": 45, "precip_probability": 30, "wind_speed": 5, "wind_direction": 45, "uv_index": 1.0, "sunrise": "2026-08-07T05:55", "sunset": "2026-08-07T20:01"},
    {"date": "2026-08-08", "hi": 65, "lo": 48, "weather_code": 63, "precip_probability": 80, "wind_speed": 18, "wind_direction": 315, "uv_index": 0.0, "sunrise": "2026-08-08T05:56", "sunset": "2026-08-08T19:59"},
    {"date": "2026-08-09", "hi": 30, "lo": 20, "weather_code": 73, "precip_probability": 90, "wind_speed": 25, "wind_direction": 0, "uv_index": 0.0, "sunrise": "2026-08-09T05:57", "sunset": "2026-08-09T19:58"},
    {"date": "2026-08-10", "hi": 78, "lo": 60, "weather_code": 96, "precip_probability": 70, "wind_speed": 22, "wind_direction": 135, "uv_index": 2.0, "sunrise": "2026-08-10T05:58", "sunset": "2026-08-10T19:56"},
]

MOCK_HOURLY = [
    {"time": "2026-08-04T21:00", "temperature": 78.0, "weather_code": 0, "precip_probability": 0, "wind_speed": 6.1, "wind_direction": 180, "uv_index": 0.0, "humidity": 45, "is_day": False},
    {"time": "2026-08-04T22:00", "temperature": 74.5, "weather_code": 1, "precip_probability": 5, "wind_speed": 7.8, "wind_direction": 200, "uv_index": 0.0, "humidity": 50, "is_day": False},
    {"time": "2026-08-04T23:00", "temperature": 72.2, "weather_code": 2, "precip_probability": 15, "wind_speed": 9.4, "wind_direction": 225, "uv_index": 0.0, "humidity": 55, "is_day": False},
    {"time": "2026-08-05T00:00", "temperature": 70.6, "weather_code": 3, "precip_probability": 20, "wind_speed": 11.2, "wind_direction": 250, "uv_index": 0.0, "humidity": 60, "is_day": False},
    {"time": "2026-08-05T01:00", "temperature": 69.7, "weather_code": 45, "precip_probability": 25, "wind_speed": 5.5, "wind_direction": 270, "uv_index": 0.0, "humidity": 65, "is_day": False},
    {"time": "2026-08-05T02:00", "temperature": 68.4, "weather_code": 61, "precip_probability": 40, "wind_speed": 13.6, "wind_direction": 290, "uv_index": 0.0, "humidity": 70, "is_day": False},
    {"time": "2026-08-05T03:00", "temperature": 67.5, "weather_code": 63, "precip_probability": 75, "wind_speed": 18.3, "wind_direction": 300, "uv_index": 0.0, "humidity": 78, "is_day": False},
    {"time": "2026-08-05T04:00", "temperature": 66.6, "weather_code": 65, "precip_probability": 90, "wind_speed": 22.7, "wind_direction": 315, "uv_index": 0.0, "humidity": 82, "is_day": False},
    {"time": "2026-08-05T05:00", "temperature": 65.9, "weather_code": 95, "precip_probability": 85, "wind_speed": 25.0, "wind_direction": 330, "uv_index": 0.0, "humidity": 88, "is_day": False},
    {"time": "2026-08-05T06:00", "temperature": 65.4, "weather_code": 3, "precip_probability": 10, "wind_speed": 10.1, "wind_direction": 350, "uv_index": 0.0, "humidity": 80, "is_day": True},
]
