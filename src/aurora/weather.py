"""Open-Meteo weather adapter for AURORA."""

from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import urlopen


class WeatherError(RuntimeError):
    pass


WMO = {
    0: "ясно", 1: "преимущественно ясно", 2: "переменная облачность", 3: "пасмурно",
    45: "туман", 48: "изморозь", 51: "слабая морось", 53: "морось", 55: "сильная морось",
    61: "небольшой дождь", 63: "дождь", 65: "сильный дождь", 71: "снег", 73: "снег", 75: "сильный снег",
    80: "ливень", 81: "ливень", 82: "сильный ливень", 95: "гроза",
}


class OpenMeteoWeather:
    def __init__(self, city: str, country: str = "") -> None:
        self.city = city
        self.country = country

    @staticmethod
    def _get_json(url: str) -> dict:
        try:
            with urlopen(url, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as error:
            raise WeatherError("Не удалось получить прогноз погоды.") from error

    def forecast(self) -> str:
        location_params = {"name": self.city, "count": 1, "language": "ru", "format": "json"}
        if self.country:
            location_params["countryCode"] = self.country[:2].upper()
        location = self._get_json("https://geocoding-api.open-meteo.com/v1/search?" + urlencode(location_params))
        if not location.get("results"):
            raise WeatherError(f"Город «{self.city}» не найден.")
        place = location["results"][0]
        params = {
            "latitude": place["latitude"], "longitude": place["longitude"], "timezone": "auto",
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,precipitation",
            "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max",
            "forecast_days": 2,
        }
        data = self._get_json("https://api.open-meteo.com/v1/forecast?" + urlencode(params))
        current = data["current"]
        daily = data["daily"]
        description = WMO.get(current["weather_code"], "неизвестные условия")
        tomorrow = WMO.get(daily["weather_code"][1], "неизвестные условия")
        return (
            f"Погода: {place['name']}\n"
            f"Сейчас: {current['temperature_2m']:.0f}°C, ощущается как {current['apparent_temperature']:.0f}°C, {description}.\n"
            f"Ветер: {current['wind_speed_10m']:.0f} км/ч.\n"
            f"Завтра: {daily['temperature_2m_min'][1]:.0f}…{daily['temperature_2m_max'][1]:.0f}°C, {tomorrow}; вероятность осадков до {daily['precipitation_probability_max'][1]:.0f}%."
        )
