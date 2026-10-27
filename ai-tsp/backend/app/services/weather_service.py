from __future__ import annotations

from typing import Any

import httpx

from app.weather_schemas import CityWeather


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_DESCRIPTIONS = {
    0: "晴",
    1: "大部晴朗",
    2: "多云",
    3: "阴",
    45: "雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "强毛毛雨",
    56: "轻度冻毛毛雨",
    57: "强冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "轻度冻雨",
    67: "强冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "米雪",
    80: "小阵雨",
    81: "中阵雨",
    82: "强阵雨",
    85: "小阵雪",
    86: "强阵雪",
    95: "雷暴",
    96: "雷暴伴小冰雹",
    99: "雷暴伴强冰雹",
}


class WeatherServiceError(RuntimeError):
    pass


class WeatherCityNotFoundError(WeatherServiceError):
    pass


class WeatherUpstreamError(WeatherServiceError):
    pass


def weather_description(code: int) -> str:
    return WEATHER_DESCRIPTIONS.get(code, "未知天气")


def preparation_recommendation(current_temperature: float) -> str:
    if current_temperature < 0:
        return "气温低于0度，需要：除冰除霜、暖风预热"
    if current_temperature < 15:
        return "天气寒冷，需要：暖风预热"
    if current_temperature <= 30:
        return "天气舒适，需要：打开通风模式"
    return "天气炎热，需要：打开制冷模式"


class WeatherService:
    def _fetch_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    def get_weather(self, city: str) -> CityWeather:
        normalized_city = city.strip()
        try:
            geocoding = self._fetch_json(
                GEOCODING_URL,
                {
                    "name": normalized_city,
                    "count": 1,
                    "language": "zh",
                    "format": "json",
                    "countryCode": "CN",
                },
            )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise WeatherUpstreamError("天气服务暂时不可用") from exc

        results = geocoding.get("results") or []
        if not results:
            raise WeatherCityNotFoundError(f"未找到城市：{normalized_city}")

        location = results[0]
        try:
            forecast = self._fetch_json(
                FORECAST_URL,
                {
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                    "current": (
                        "temperature_2m,relative_humidity_2m,weather_code"
                    ),
                    "daily": (
                        "temperature_2m_max,temperature_2m_min,weather_code,"
                        "snowfall_sum,rain_sum,precipitation_probability_max"
                    ),
                    "timezone": "Asia/Shanghai",
                    "forecast_days": 1,
                },
            )
            return self._parse_weather(normalized_city, forecast)
        except WeatherServiceError:
            raise
        except (
            httpx.HTTPError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ) as exc:
            raise WeatherUpstreamError("天气服务返回数据异常") from exc

    def _parse_weather(
        self,
        city: str,
        payload: dict[str, Any],
    ) -> CityWeather:
        current = payload["current"]
        daily = payload["daily"]
        date = str(daily["time"][0])
        current_temperature = float(current["temperature_2m"])
        current_humidity = int(current["relative_humidity_2m"])
        current_weather = weather_description(int(current["weather_code"]))
        max_temperature = float(daily["temperature_2m_max"][0])
        min_temperature = float(daily["temperature_2m_min"][0])
        daily_weather = weather_description(int(daily["weather_code"][0]))
        snowfall_cm = float(daily["snowfall_sum"][0] or 0)
        rain_mm = float(daily["rain_sum"][0] or 0)
        precipitation_probability = int(
            daily["precipitation_probability_max"][0] or 0
        )
        freeze_warning = (
            f"⚠ 冰冻提醒：最低温{min_temperature:.1f}℃，"
            "夜间至清晨有道路结冰/冰冻风险"
            if min_temperature < 0
            else None
        )

        report_lines = [
            "======================================",
            f"  【{city}】当天天气  {date}（北京时间）",
            "======================================",
            (
                f"  当前实况：{current_temperature:.1f}℃  {current_weather}"
                f"（相对湿度 {current_humidity}%）"
            ),
            (
                f"  当天温度：最高 {max_temperature:.1f}℃ ｜ "
                f"最低 {min_temperature:.1f}℃"
            ),
            f"  天气现象：{daily_weather}",
            f"  降水量　：降雪 {snowfall_cm:.1f}cm、降雨 {rain_mm:.1f}mm",
            f"  降水概率：{precipitation_probability}%",
        ]
        if freeze_warning:
            report_lines.append(f"  {freeze_warning}")
        report_lines.append("======================================")

        return CityWeather(
            city=city,
            date=date,
            current_temperature=current_temperature,
            current_humidity=current_humidity,
            current_weather=current_weather,
            max_temperature=max_temperature,
            min_temperature=min_temperature,
            daily_weather=daily_weather,
            snowfall_cm=snowfall_cm,
            rain_mm=rain_mm,
            precipitation_probability=precipitation_probability,
            freeze_warning=freeze_warning,
            recommendation=preparation_recommendation(current_temperature),
            weather_log="\n".join(report_lines),
        )


weather_service = WeatherService()
