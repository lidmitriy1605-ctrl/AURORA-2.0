import unittest

from aurora.weather import OpenMeteoWeather


class WeatherTests(unittest.TestCase):
    def test_formats_current_weather_and_tomorrow(self):
        weather = OpenMeteoWeather("Saint Petersburg", "RU")
        responses = iter([
            {"results": [{"name": "Санкт-Петербург", "latitude": 59.94, "longitude": 30.31}]},
            {"current": {"temperature_2m": 18.0, "apparent_temperature": 17.0, "weather_code": 2, "wind_speed_10m": 10.0, "precipitation": 0},
             "daily": {"temperature_2m_max": [18.0, 21.0], "temperature_2m_min": [12.0, 14.0], "weather_code": [2, 61], "precipitation_probability_max": [5, 70]}},
        ])
        weather._get_json = lambda _: next(responses)
        result = weather.forecast()
        self.assertIn("Сейчас: 18°C", result)
        self.assertIn("Завтра: 14…21°C", result)
