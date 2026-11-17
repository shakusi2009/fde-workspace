import httpx
import pytest

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import VehicleAgentChatResponse
from app.services.vehicle_agent_service import (
    VehicleAgentConfigurationError,
    VehicleAgentExecutionError,
    VehicleAgentUpstreamError,
    vehicle_agent_service,
)


client = TestClient(app)


def driver_row() -> dict:
    return {
        "id": 7,
        "name": "王明明",
        "phone": "13800138000",
        "vin": "2T16BU270T7YTRALX",
        "vehicle_model": "坦克 500",
        "address": "新疆维吾尔自治区阿勒泰市",
        "registration_city": "阿勒泰",
        "registration_date": "2026-10-23",
        "create_time": "2026-10-23T12:00:00",
        "update_time": "2026-10-23T12:00:00",
    }


def test_health() -> None:
    response = client.get("/api/vehicle-agent/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_driver_options_map_tsp_driver_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        vehicle_agent_service,
        "_request_json",
        lambda _path, _params: {
            "items": [driver_row()],
            "total": 1,
            "page": 1,
            "page_size": 10,
        },
    )

    response = client.get(
        "/api/vehicle-agent/drivers/options?keyword=%E7%8E%8B%E6%98%8E"
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 7,
            "name": "王明明",
            "vin": "2T16BU270T7YTRALX",
            "vehicle_model": "坦克 500",
            "address": "新疆维吾尔自治区阿勒泰市",
            "registration_city": "阿勒泰",
        }
    ]


def test_driver_options_map_upstream_failure(monkeypatch) -> None:
    def raise_upstream(_path: str, _params: dict) -> dict:
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(vehicle_agent_service, "_request_json", raise_upstream)

    response = client.get("/api/vehicle-agent/drivers/options")

    assert response.status_code == 503
    assert response.json()["detail"] == "车主数据服务暂不可用"


def test_chat_requires_registered_context() -> None:
    response = client.post(
        "/api/vehicle-agent/chat",
        json={
            "session_id": "session-1",
            "model_id": "",
            "driver": {
                "id": 7,
                "name": "王明明",
                "vin": "2T16BU270T7YTRALX",
                "vehicle_model": "坦克 500",
                "address": "新疆维吾尔自治区阿勒泰市",
                "registration_city": "阿勒泰",
            },
            "message": "打开空调",
        },
    )

    assert response.status_code == 422


def test_chat_returns_model_answer(monkeypatch) -> None:
    monkeypatch.setattr(
        vehicle_agent_service,
        "chat",
        lambda payload: VehicleAgentChatResponse(
            session_id=payload.session_id,
            model_id=payload.model_id,
            answer="真实模型回答",
            reasoning_summary=["识别问题", "生成回答"],
            internet_used=False,
            sources=[],
        ),
    )
    response = client.post(
        "/api/vehicle-agent/chat",
        json={
            "session_id": "session-1",
            "model_id": "doubao-seed-2-1-lite-260915",
            "driver": {
                "id": 7,
                "name": "王明明",
                "vin": "2T16BU270T7YTRALX",
                "vehicle_model": "坦克 500",
                "address": "新疆维吾尔自治区阿勒泰市",
                "registration_city": "阿勒泰",
            },
            "message": "帮我检查车辆状态",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "session-1"
    assert payload["model_id"] == "doubao-seed-2-1-lite-260915"
    assert payload["answer"] == "真实模型回答"
    assert payload["reasoning_summary"] == ["识别问题", "生成回答"]
    assert payload["internet_used"] is False
    assert payload["sources"] == []


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (VehicleAgentConfigurationError("配置不完整"), 503),
        (VehicleAgentExecutionError("模型调用失败"), 502),
    ],
)
def test_chat_maps_agent_errors(monkeypatch, error, status_code) -> None:
    def raise_error(_payload):
        raise error

    monkeypatch.setattr(vehicle_agent_service, "chat", raise_error)

    response = client.post(
        "/api/vehicle-agent/chat",
        json={
            "session_id": "session-1",
            "model_id": "doubao-seed-2-1-lite-260915",
            "driver": {
                "id": 7,
                "name": "王明明",
                "vin": "2T16BU270T7YTRALX",
                "vehicle_model": "坦克 500",
                "address": "新疆维吾尔自治区阿勒泰市",
                "registration_city": "阿勒泰",
            },
            "message": "帮我检查车辆状态",
        },
    )

    assert response.status_code == status_code
    assert response.json()["detail"] == str(error)
