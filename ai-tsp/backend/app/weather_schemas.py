from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class CityWeather(BaseModel):
    city: str
    date: str
    current_temperature: float
    current_humidity: int
    current_weather: str
    max_temperature: float
    min_temperature: float
    daily_weather: str
    snowfall_cm: float
    rain_mm: float
    precipitation_probability: int
    freeze_warning: Optional[str] = None
    recommendation: str
    weather_log: str
