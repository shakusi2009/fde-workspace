import httpx
import pytest

from fastapi.testclient import TestClient

from app.main import app
from app.services.weather_service import (
    WeatherCityNotFoundError,
    WeatherService,
    WeatherUpstreamError,
    preparation_recommendation,
    weather_service,
)


client = TestClient(app)


def open_meteo_payloads() -> tuple[dict, dict]:
    geocoding = {
        "results": [
            {
                "name": "阿勒泰市",
                "latitude": 47.84864,
                "longitude": 88.13361,
                "country_code": "CN",
            }
        ]
    }
    forecast = {
        "current": {
            "temperature_2m": -3.3,
            "relative_humidity_2m": 91,
            "weather_code": 3,
        },
        "daily": {
            "time": ["2026-10-24"],
            "temperature_2m_max": [-3.2],
            "temperature_2m_min": [-12.0],
            "weather_code": [71],
            "snowfall_sum": [0.1],
            "rain_sum": [0.2],
            "precipitation_probability_max": [19],
        },
    }
    return geocoding, forecast


def test_weather_service_formats_real_weather_report(monkeypatch) -> None:
    geocoding, forecast = open_meteo_payloads()
    service = WeatherService()

    def fetch_json(url: str, params: dict) -> dict:
        if "geocoding-api" in url:
            assert params == {
                "name": "阿勒泰",
                "count": 1,
                "language": "zh",
                "format": "json",
                "countryCode": "CN",
            }
            return geocoding
        assert params["timezone"] == "Asia/Shanghai"
        assert params["forecast_days"] == 1
        return forecast

    monkeypatch.setattr(service, "_fetch_json", fetch_json)
    result = service.get_weather("阿勒泰")

    assert result.city == "阿勒泰"
    assert result.current_temperature == -3.3
    assert result.recommendation == "气温低于0度，需要：除冰除霜、暖风预热"
    assert result.weather_log == (
        "======================================\n"
        "  【阿勒泰】当天天气  2026-10-24（北京时间）\n"
        "======================================\n"
        "  当前实况：-3.3℃  阴（相对湿度 91%）\n"
        "  当天温度：最高 -3.2℃ ｜ 最低 -12.0℃\n"
        "  天气现象：小雪\n"
        "  降水量　：降雪 0.1cm、降雨 0.2mm\n"
        "  降水概率：19%\n"
        "  ⚠ 冰冻提醒：最低温-12.0℃，夜间至清晨有道路结冰/冰冻风险\n"
        "======================================"
    )


@pytest.mark.parametrize(
    ("temperature", "expected"),
    [
        (-0.1, "气温低于0度，需要：除冰除霜、暖风预热"),
        (0.0, "天气寒冷，需要：暖风预热"),
        (14.9, "天气寒冷，需要：暖风预热"),
        (15.0, "天气舒适，需要：打开通风模式"),
        (30.0, "天气舒适，需要：打开通风模式"),
        (30.1, "天气炎热，需要：打开制冷模式"),
    ],
)
def test_preparation_recommendation_boundaries(
    temperature: float,
    expected: str,
) -> None:
    assert preparation_recommendation(temperature) == expected


def test_weather_service_reports_unknown_city(monkeypatch) -> None:
    service = WeatherService()
    monkeypatch.setattr(service, "_fetch_json", lambda _url, _params: {})

    with pytest.raises(WeatherCityNotFoundError, match="未找到城市"):
        service.get_weather("不存在的城市")


def test_weather_service_wraps_upstream_errors(monkeypatch) -> None:
    service = WeatherService()

    def raise_timeout(_url: str, _params: dict) -> dict:
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(service, "_fetch_json", raise_timeout)

    with pytest.raises(WeatherUpstreamError, match="天气服务暂时不可用"):
        service.get_weather("北京")


def test_weather_endpoint_returns_service_result(monkeypatch) -> None:
    service = WeatherService()
    geocoding, forecast = open_meteo_payloads()
    responses = iter([geocoding, forecast])
    monkeypatch.setattr(service, "_fetch_json", lambda _url, _params: next(responses))
    monkeypatch.setattr(weather_service, "get_weather", service.get_weather)

    response = client.get("/api/agent-data/weather?city=%E9%98%BF%E5%8B%92%E6%B3%B0")

    assert response.status_code == 200
    assert response.json()["city"] == "阿勒泰"
    assert response.json()["daily_weather"] == "小雪"


def test_weather_endpoint_maps_service_errors(monkeypatch) -> None:
    monkeypatch.setattr(
        weather_service,
        "get_weather",
        lambda _city: (_ for _ in ()).throw(
            WeatherCityNotFoundError("未找到城市：未知"),
        ),
    )
    response = client.get("/api/agent-data/weather?city=%E6%9C%AA%E7%9F%A5")
    assert response.status_code == 404

    monkeypatch.setattr(
        weather_service,
        "get_weather",
        lambda _city: (_ for _ in ()).throw(
            WeatherUpstreamError("天气服务暂时不可用"),
        ),
    )
    response = client.get("/api/agent-data/weather?city=%E5%8C%97%E4%BA%AC")
    assert response.status_code == 502
