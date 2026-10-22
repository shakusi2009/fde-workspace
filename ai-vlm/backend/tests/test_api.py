from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.repositories.vlm_task_repository import VlmRepositoryError
from app.services.vlm_service import vlm_service


client = TestClient(app)


def test_health_reports_rds_configuration_state() -> None:
    response = client.get("/api/vlm/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert isinstance(response.json()["rds_configured"], bool)


def test_overview_returns_task_total_and_seven_day_trend(monkeypatch) -> None:
    today = date.today()
    start_date = today - timedelta(days=6)

    def get_task_overview(query_start: date, query_end: date):
        assert query_start == start_date
        assert query_end == today + timedelta(days=1)
        return 18, {
            start_date: 3,
            today - timedelta(days=2): 5,
            today: 2,
        }

    monkeypatch.setattr(
        vlm_service.repository,
        "get_task_overview",
        get_task_overview,
        raising=False,
    )
    response = client.get("/api/vlm/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_total"] == 18
    assert payload["overall_accuracy"] is None
    assert payload["token_total"] == 0
    assert payload["data_status"] == "ready"
    assert payload["task_trend"] == [
        {"label": (start_date + timedelta(days=offset)).strftime("%m-%d"), "value": value}
        for offset, value in enumerate([3, 0, 0, 0, 5, 0, 2])
    ]


def test_overview_returns_service_unavailable_for_repository_error(
    monkeypatch,
) -> None:
    def get_task_overview(*_args):
        raise VlmRepositoryError("读取 VLM 总览数据失败")

    monkeypatch.setattr(
        vlm_service.repository,
        "get_task_overview",
        get_task_overview,
        raising=False,
    )
    response = client.get("/api/vlm/overview")

    assert response.status_code == 503
    assert response.json() == {"detail": "读取 VLM 总览数据失败"}


def test_task_list_maps_database_fields(monkeypatch) -> None:
    def list_tasks(page: int, page_size: int):
        assert page == 2
        assert page_size == 10
        return (
            [
                {
                    "id": 21,
                    "vlm_type": "lable",
                    "create_time": datetime(2026, 10, 21, 9, 30),
                    "task_tokens": 12500,
                    "task_accuracy": 96.5,
                    "remarks": "回归样本",
                    "task_status": 2,
                    "update_time": datetime(2026, 10, 21, 11, 45),
                },
                {
                    "id": 20,
                    "vlm_type": "dig",
                    "create_time": datetime(2026, 10, 20, 16, 0),
                    "task_tokens": 8800,
                    "task_accuracy": None,
                    "remarks": None,
                    "task_status": 1,
                    "update_time": None,
                },
            ],
            24,
        )

    monkeypatch.setattr(vlm_service.repository, "list_tasks", list_tasks)
    response = client.get("/api/vlm/tasks?page=2&page_size=100")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "sequence": 21,
                "task_type": "标注",
                "created_at": "2026-10-21T09:30:00",
                "token_usage": 12500,
                "accuracy": 96.5,
                "remark": "回归样本",
                "task_status": 2,
                "updated_at": "2026-10-21T11:45:00",
            },
            {
                "sequence": 20,
                "task_type": "挖掘",
                "created_at": "2026-10-20T16:00:00",
                "token_usage": 8800,
                "accuracy": None,
                "remark": "",
                "task_status": 1,
                "updated_at": None,
            },
        ],
        "total": 24,
        "page": 2,
        "page_size": 10,
    }


def test_task_list_returns_service_unavailable_for_repository_error(
    monkeypatch,
) -> None:
    def list_tasks(**_kwargs):
        raise VlmRepositoryError("无法连接 VLM RDS 数据库")

    monkeypatch.setattr(vlm_service.repository, "list_tasks", list_tasks)
    response = client.get("/api/vlm/tasks")

    assert response.status_code == 503
    assert response.json() == {"detail": "无法连接 VLM RDS 数据库"}


def test_task_list_rejects_invalid_page() -> None:
    response = client.get("/api/vlm/tasks?page=0")

    assert response.status_code == 422
