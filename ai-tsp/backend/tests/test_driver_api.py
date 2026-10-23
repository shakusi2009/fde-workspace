from datetime import date, datetime

from fastapi.testclient import TestClient

from app.main import app
from app.repositories.driver_repository import (
    DriverNotFoundError,
    DriverVinConflictError,
)
from app.services.driver_service import driver_service


client = TestClient(app)


def driver_payload(**overrides) -> dict:
    payload = {
        "name": "张三",
        "phone": "13800138000",
        "vin": "lgwef6a50nh123456",
        "vehicle_model": "坦克 500",
        "address": "北京市朝阳区",
        "registration_city": "北京",
        "registration_date": "2026-10-23",
    }
    payload.update(overrides)
    return payload


def test_list_drivers_uses_fixed_page_size_and_keyword(monkeypatch) -> None:
    def list_drivers(*, page: int, page_size: int, keyword: str):
        assert page == 2
        assert page_size == 10
        assert keyword == "坦克"
        return (
            [
                {
                    "id": 12,
                    "name": "张三",
                    "phone": "13800138000",
                    "vin": "LGWEF6A50NH123456",
                    "vehicle_model": "坦克 500",
                    "address": "北京市朝阳区",
                    "registration_city": "北京",
                    "registration_date": date(2026, 10, 23),
                    "create_time": datetime(2026, 10, 23, 12, 0),
                    "update_time": datetime(2026, 10, 23, 12, 0),
                }
            ],
            11,
        )

    monkeypatch.setattr(
        driver_service.repository,
        "list_drivers",
        list_drivers,
    )
    response = client.get(
        "/api/agent-data/drivers?page=2&page_size=100&keyword=%E5%9D%A6%E5%85%8B"
    )

    assert response.status_code == 200
    assert response.json()["page_size"] == 10
    assert response.json()["total"] == 11
    assert response.json()["items"][0]["vin"] == "LGWEF6A50NH123456"


def test_driver_options_searches_with_fixed_limit(monkeypatch) -> None:
    def list_driver_options(*, keyword: str, limit: int):
        assert keyword == "张"
        assert limit == 50
        return [
            {
                "id": 12,
                "name": "张三",
                "vin": "LGWEF6A50NH123456",
                "vehicle_model": "坦克 500",
                "phone": "13800138000",
            }
        ]

    monkeypatch.setattr(
        driver_service.repository,
        "list_driver_options",
        list_driver_options,
        raising=False,
    )
    response = client.get(
        "/api/agent-data/drivers/options?keyword=%E5%BC%A0"
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 12,
            "name": "张三",
            "vin": "LGWEF6A50NH123456",
            "vehicle_model": "坦克 500",
        }
    ]


def test_create_driver_normalizes_input(monkeypatch) -> None:
    captured = {}

    def create_driver(**payload):
        captured.update(payload)
        return 18

    monkeypatch.setattr(
        driver_service.repository,
        "create_driver",
        create_driver,
    )
    response = client.post(
        "/api/agent-data/drivers",
        json=driver_payload(name="  张三  ", vin=" lgwef6a50nh123456 "),
    )

    assert response.status_code == 201
    assert response.json() == {"id": 18, "message": "车主创建成功"}
    assert captured["name"] == "张三"
    assert captured["vin"] == "LGWEF6A50NH123456"


def test_create_driver_reports_duplicate_vin(monkeypatch) -> None:
    def create_driver(**_payload):
        raise DriverVinConflictError("VIN 码已存在")

    monkeypatch.setattr(
        driver_service.repository,
        "create_driver",
        create_driver,
    )
    response = client.post("/api/agent-data/drivers", json=driver_payload())

    assert response.status_code == 409
    assert response.json() == {"detail": "VIN 码已存在"}


def test_update_driver_reports_not_found(monkeypatch) -> None:
    def update_driver(_driver_id: int, **_payload):
        raise DriverNotFoundError("车主不存在")

    monkeypatch.setattr(
        driver_service.repository,
        "update_driver",
        update_driver,
    )
    response = client.put(
        "/api/agent-data/drivers/999",
        json=driver_payload(),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "车主不存在"}


def test_delete_driver_returns_success(monkeypatch) -> None:
    deleted = []
    monkeypatch.setattr(
        driver_service.repository,
        "delete_driver",
        lambda driver_id: deleted.append(driver_id),
    )

    response = client.delete("/api/agent-data/drivers/7")

    assert response.status_code == 200
    assert response.json() == {"message": "车主已删除"}
    assert deleted == [7]
