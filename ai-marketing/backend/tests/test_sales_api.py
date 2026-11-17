from __future__ import annotations

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services.dongchedi_service import (
    DongchediEmptyResultError,
    dongchedi_service,
)


client = TestClient(app)


def upstream_payload() -> dict:
    return {
        "status": 0,
        "message": "success",
        "data": {
            "head_info": {"title": "", "text": ""},
            "paging": {
                "count": 20,
                "has_more": False,
                "offset": 0,
                "total": 0,
            },
            "list": [
                {
                    "series_id": 4363,
                    "series_name": "Model Y",
                    "image": "https://example.com/model-y.png",
                    "rank": 1,
                    "last_rank": 2,
                    "count": 39827,
                    "brand_name": "特斯拉",
                    "brand_id": 63,
                    "sub_brand_name": "特斯拉中国",
                    "price": "26.35-36.90万",
                    "outter_detail_type": 12,
                },
                {
                    "series_id": 20154,
                    "series_name": "星愿",
                    "image": "https://example.com/xingyuan.png",
                    "rank": 2,
                    "last_rank": 1,
                    "count": 30953,
                    "brand_name": "吉利银河",
                    "brand_id": 858,
                    "sub_brand_name": "吉利银河",
                    "price": "6.18-9.18万",
                    "outter_detail_type": 1,
                },
            ],
        },
    }


def periods_payload() -> dict:
    payload = upstream_payload()
    payload["data"]["sells_rank_month"] = [
        {"text": "2026年10月", "month": 202610},
        {"text": "2026年09月", "month": 202609},
        {"text": "近半年", "month": 500},
    ]
    return payload


def test_health() -> None:
    response = client.get("/api/marketing-ai/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_sales_ranking_normalizes_public_data(monkeypatch) -> None:
    captured: dict = {}

    def fake_fetch(params: dict) -> dict:
        captured.update(params)
        return upstream_payload()

    monkeypatch.setattr(dongchedi_service, "_fetch_json", fake_fetch)
    dongchedi_service.clear_cache()

    response = client.get(
        "/api/marketing-ai/public-insight/sales?year=2026&month=3"
    )

    assert response.status_code == 200
    assert captured["month"] == "202603"
    assert captured["rank_data_type"] == 11
    assert captured["city_name"] == "全国"
    assert captured["count"] == 100
    payload = response.json()
    assert payload["period"] == "2026-03"
    assert payload["source_name"] == "懂车帝"
    assert payload["filters"] == {
        "vehicle_type": "all",
        "level": "",
        "energy_type": "",
        "manufacturer": "",
        "brand_id": "",
    }
    assert payload["items"][0] == {
        "rank": 1,
        "series_id": 4363,
        "series_name": "Model Y",
        "brand_name": "特斯拉",
        "manufacturer": "特斯拉中国",
        "sales": 39827,
        "previous_rank": 2,
        "image": "https://example.com/model-y.png",
        "price": "26.35-36.90万",
    }


def test_sales_ranking_applies_official_filters(monkeypatch) -> None:
    captured: dict = {}

    def fake_fetch(params: dict) -> dict:
        captured.update(params)
        return upstream_payload()

    monkeypatch.setattr(dongchedi_service, "_fetch_json", fake_fetch)
    dongchedi_service.clear_cache()

    response = client.get(
        "/api/marketing-ai/public-insight/sales"
        "?year=2026&month=3&vehicle_type=suv&level=medium"
        "&energy_type=2&manufacturer=%E8%87%AA%E4%B8%BB&brand_id=16"
    )

    assert response.status_code == 200
    assert captured["new_energy_type"] == "2"
    assert captured["manufacturer"] == "自主"
    assert captured["brand_id"] == 16
    payload = response.json()
    assert [item["series_name"] for item in payload["items"]] == ["Model Y"]
    assert payload["items"][0]["rank"] == 1


def test_sales_ranking_paginates_before_vehicle_filter(monkeypatch) -> None:
    calls: list[int] = []

    def fake_fetch(params: dict) -> dict:
        offset = int(params["offset"])
        calls.append(offset)
        payload = upstream_payload()
        if offset == 0:
            payload["data"]["list"] = [
                {
                    **payload["data"]["list"][0],
                    "series_id": index,
                    "series_name": f"SUV {index}",
                }
                for index in range(100)
            ]
            payload["data"]["paging"] = {
                "count": 100,
                "has_more": True,
                "offset": 0,
                "total": 0,
            }
        else:
            payload["data"]["list"] = [{
                **payload["data"]["list"][0],
                "series_id": 9001,
                "series_name": "第二页 MPV",
                "outter_detail_type": 24,
            }]
            payload["data"]["paging"] = {
                "count": 1,
                "has_more": False,
                "offset": 100,
                "total": 0,
            }
        return payload

    monkeypatch.setattr(dongchedi_service, "_fetch_json", fake_fetch)
    dongchedi_service.clear_cache()

    response = client.get(
        "/api/marketing-ai/public-insight/sales"
        "?year=2026&month=3&vehicle_type=mpv"
    )

    assert response.status_code == 200
    assert calls == [0, 100]
    assert [
        item["series_name"] for item in response.json()["items"]
    ] == ["第二页 MPV"]


def test_sales_filter_options_derive_brands(monkeypatch) -> None:
    monkeypatch.setattr(
        dongchedi_service,
        "_fetch_json",
        lambda _params: upstream_payload(),
    )

    response = client.get(
        "/api/marketing-ai/public-insight/sales/filters"
        "?year=2026&month=3"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["vehicle_types"][1]["value"] == "sedan"
    assert payload["energy_types"][1]["label"] == "纯电"
    assert payload["manufacturers"][1]["value"] == "自主"
    assert payload["brands"] == [
        {"id": 858, "name": "吉利银河"},
        {"id": 63, "name": "特斯拉"},
    ]


def test_sales_periods_only_returns_calendar_months(monkeypatch) -> None:
    monkeypatch.setattr(
        dongchedi_service,
        "_fetch_json",
        lambda _params: periods_payload(),
    )

    response = client.get(
        "/api/marketing-ai/public-insight/sales/periods"
    )

    assert response.status_code == 200
    assert response.json() == {
        "source_name": "懂车帝",
        "periods": [
            {
                "year": 2026,
                "month": 10,
                "period": "2026-10",
                "label": "2026年10月",
            },
            {
                "year": 2026,
                "month": 9,
                "period": "2026-09",
                "label": "2026年09月",
            },
        ],
    }


def test_sales_ranking_validates_period() -> None:
    assert client.get(
        "/api/marketing-ai/public-insight/sales?year=2019&month=1"
    ).status_code == 422
    assert client.get(
        "/api/marketing-ai/public-insight/sales?year=2026&month=13"
    ).status_code == 422


def test_sales_ranking_maps_empty_result(monkeypatch) -> None:
    monkeypatch.setattr(
        dongchedi_service,
        "get_sales_ranking",
        lambda **_kwargs: (_ for _ in ()).throw(
            DongchediEmptyResultError("该月份暂无公开销量数据")
        ),
    )

    response = client.get(
        "/api/marketing-ai/public-insight/sales?year=2020&month=1"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "该月份暂无公开销量数据"


def test_sales_ranking_maps_upstream_failure(monkeypatch) -> None:
    def raise_timeout(_params: dict) -> dict:
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(dongchedi_service, "_fetch_json", raise_timeout)
    dongchedi_service.clear_cache()

    response = client.get(
        "/api/marketing-ai/public-insight/sales?year=2025&month=12"
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "懂车帝公开销量数据暂不可用"
