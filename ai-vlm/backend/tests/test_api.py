from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app, tos_signing_service
from app.schemas import VlmTaskItem
from app.repositories.vlm_task_repository import (
    VlmPromptNotFoundError,
    VlmRepositoryError,
    VlmTaskNotFoundError,
    VlmTaskPromptUnavailableError,
)
from app.services.vlm_service import vlm_service
from app.services.agent_service import (
    AgentConfigurationError,
    AgentExecutionError,
)
from app.services.tos_service import TosConfigurationError


client = TestClient(app)


def test_tos_private_sign_returns_signed_url(monkeypatch) -> None:
    monkeypatch.setattr(
        tos_signing_service,
        "generate_private_signed_url",
        lambda url: (
            "https://bucket.tos-cn-beijing.ivolces.com/video.mp4"
            "?X-Tos-Signature=test"
        ),
    )
    response = client.post(
        "/api/vlm/tos/private-sign",
        json={
            "original_url": (
                "https://bucket.tos-cn-beijing.volces.com/video.mp4"
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["signed_url"].endswith("X-Tos-Signature=test")


def test_tos_private_sign_reports_missing_credentials(monkeypatch) -> None:
    def generate(_url: str):
        raise TosConfigurationError("TOS 访问凭证未配置")

    monkeypatch.setattr(
        tos_signing_service,
        "generate_private_signed_url",
        generate,
    )
    response = client.post(
        "/api/vlm/tos/private-sign",
        json={
            "original_url": (
                "https://bucket.tos-cn-beijing.volces.com/video.mp4"
            )
        },
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "TOS 访问凭证未配置"}


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
                    "prompt_id": 9,
                    "prompt_title": "道路目标识别",
                    "task_input": "夜间道路视频",
                    "vlm_type": "label",
                    "create_time": datetime(2026, 10, 21, 9, 30),
                    "task_tokens": 12500,
                    "task_accuracy": 96.5,
                    "remarks": "回归样本",
                    "task_status": 2,
                    "update_time": datetime(2026, 10, 21, 11, 45),
                },
                {
                    "id": 20,
                    "prompt_id": None,
                    "prompt_title": None,
                    "task_input": None,
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
                "prompt_id": 9,
                "prompt_title": "道路目标识别",
                "task_input": "夜间道路视频",
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
                "prompt_id": None,
                "prompt_title": None,
                "task_input": None,
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


def test_task_item_list_maps_all_database_fields(monkeypatch) -> None:
    def list_task_items(task_id: int, page: int, page_size: int):
        assert task_id == 12
        assert page == 2
        assert page_size == 10
        return (
            [
                {
                    "id": 31,
                    "task_id": 12,
                    "model_id": "ep-test-model",
                    "task_input": "https://example.com/video.mp4",
                    "total_tokens": 1200,
                    "input_tokens": 800,
                    "output_tokens": 400,
                    "cached_tokens": 100,
                    "task_status": 0,
                    "output_text": '{"is_lane_change": true}',
                },
                {
                    "id": 30,
                    "task_id": 12,
                    "model_id": "ep-test-model",
                    "task_input": "tos://bucket/object.mp4",
                    "total_tokens": None,
                    "input_tokens": None,
                    "output_tokens": None,
                    "cached_tokens": None,
                    "task_status": None,
                    "output_text": None,
                },
            ],
            14,
        )

    monkeypatch.setattr(
        vlm_service.repository,
        "list_task_items",
        list_task_items,
        raising=False,
    )
    response = client.get("/api/vlm/tasks/12/items?page=2&page_size=100")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": 31,
                "task_id": 12,
                "model_id": "ep-test-model",
                "task_input": "https://example.com/video.mp4",
                "total_tokens": 1200,
                "input_tokens": 800,
                "output_tokens": 400,
                "cached_tokens": 100,
                "task_status": 0,
                "output_text": '{"is_lane_change": true}',
            },
            {
                "id": 30,
                "task_id": 12,
                "model_id": "ep-test-model",
                "task_input": "tos://bucket/object.mp4",
                "total_tokens": None,
                "input_tokens": None,
                "output_tokens": None,
                "cached_tokens": None,
                "task_status": None,
                "output_text": None,
            },
        ],
        "total": 14,
        "page": 2,
        "page_size": 10,
        "task_id": 12,
    }


def test_task_item_list_returns_parent_not_found(monkeypatch) -> None:
    def list_task_items(**_kwargs):
        raise VlmTaskNotFoundError("任务不存在")

    monkeypatch.setattr(
        vlm_service.repository,
        "list_task_items",
        list_task_items,
        raising=False,
    )
    response = client.get("/api/vlm/tasks/404/items")

    assert response.status_code == 404
    assert response.json() == {"detail": "任务不存在"}


def test_task_item_list_returns_service_unavailable(monkeypatch) -> None:
    def list_task_items(**_kwargs):
        raise VlmRepositoryError("读取 VLM 任务明细失败")

    monkeypatch.setattr(
        vlm_service.repository,
        "list_task_items",
        list_task_items,
        raising=False,
    )
    response = client.get("/api/vlm/tasks/12/items")

    assert response.status_code == 503
    assert response.json() == {"detail": "读取 VLM 任务明细失败"}


def test_task_execution_context_maps_parent_and_prompt(monkeypatch) -> None:
    def get_task_execution_context(task_id: int):
        assert task_id == 12
        return {
            "task_id": 12,
            "prompt_id": 9,
            "prompt_title": "变道识别",
            "prompt_content": "你是自动驾驶视觉专家",
            "task_input": "https://example.com/video.mp4",
        }

    monkeypatch.setattr(
        vlm_service.repository,
        "get_task_execution_context",
        get_task_execution_context,
        raising=False,
    )
    response = client.get("/api/vlm/tasks/12/execution-context")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": 12,
        "prompt_id": 9,
        "prompt_title": "变道识别",
        "prompt_content": "你是自动驾驶视觉专家",
        "task_input": "https://example.com/video.mp4",
    }


def test_execute_task_returns_persisted_item(monkeypatch) -> None:
    def execute_task(task_id: int, model_id: str):
        assert task_id == 12
        assert model_id == "ep-test-model"
        return VlmTaskItem(
            id=32,
            task_id=12,
            model_id="ep-test-model",
            task_input="分析该视频",
            total_tokens=150,
            input_tokens=120,
            output_tokens=30,
            cached_tokens=20,
            task_status=0,
            output_text='{"is_lane_change": true}',
        )

    monkeypatch.setattr(
        vlm_service,
        "execute_task",
        execute_task,
        raising=False,
    )
    response = client.post(
        "/api/vlm/tasks/12/executions",
        json={"model_id": "ep-test-model"},
    )

    assert response.status_code == 201
    assert response.json()["id"] == 32
    assert response.json()["task_status"] == 0
    assert response.json()["total_tokens"] == 150
    assert response.json()["output_text"] == '{"is_lane_change": true}'


def test_execute_task_reports_missing_agent_configuration(monkeypatch) -> None:
    def execute_task(_task_id: int, _model_id: str):
        raise AgentConfigurationError("大模型 Agent 配置不完整")

    monkeypatch.setattr(
        vlm_service,
        "execute_task",
        execute_task,
        raising=False,
    )
    response = client.post(
        "/api/vlm/tasks/12/executions",
        json={"model_id": "ep-test-model"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "大模型 Agent 配置不完整"}


def test_execute_task_persists_specific_agent_error(monkeypatch) -> None:
    monkeypatch.setattr(
        vlm_service.repository,
        "get_task_execution_context",
        lambda _task_id: {
            "task_id": 12,
            "prompt_id": 9,
            "prompt_title": "变道识别",
            "prompt_content": "系统提示词",
            "task_input": "任务输入",
        },
        raising=False,
    )

    def fail_execution(**_kwargs):
        raise AgentExecutionError(
            "大模型 Agent 执行失败（RuntimeError）：模型不存在"
        )

    monkeypatch.setattr(
        vlm_service.agent_service,
        "execute",
        fail_execution,
    )
    captured = {}

    def create_task_item(**payload):
        captured.update(payload)
        return {"id": 33, **payload}

    monkeypatch.setattr(
        vlm_service.repository,
        "create_task_item",
        create_task_item,
        raising=False,
    )
    response = client.post(
        "/api/vlm/tasks/12/executions",
        json={"model_id": "ep-test-model"},
    )

    assert response.status_code == 201
    assert captured["task_status"] == 1
    assert captured["output_text"] == (
        "大模型 Agent 执行失败（RuntimeError）：模型不存在"
    )
    assert response.json()["output_text"] == captured["output_text"]


def test_create_task_maps_validated_payload(monkeypatch) -> None:
    def create_task(
        *,
        prompt_id: int,
        task_type: str,
        task_input: str,
        remarks: str,
    ):
        assert prompt_id == 9
        assert task_type == "label"
        assert task_input == "夜间道路视频"
        assert remarks == "夜间变道样本"
        return 25

    monkeypatch.setattr(
        vlm_service.repository,
        "create_task",
        create_task,
        raising=False,
    )
    response = client.post(
        "/api/vlm/tasks",
        json={
            "prompt_id": 9,
            "task_type": "label",
            "task_input": " 夜间道路视频 ",
            "remarks": " 夜间变道样本 ",
        },
    )

    assert response.status_code == 201
    assert response.json() == {"id": 25, "message": "任务创建成功"}


def test_create_task_rejects_unavailable_prompt(monkeypatch) -> None:
    def create_task(**_payload):
        raise VlmTaskPromptUnavailableError("请选择同类型的可用提示词模版")

    monkeypatch.setattr(
        vlm_service.repository,
        "create_task",
        create_task,
        raising=False,
    )
    response = client.post(
        "/api/vlm/tasks",
        json={
            "prompt_id": 404,
            "task_type": "dig",
            "task_input": "施工区域视频",
            "remarks": "",
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "请选择同类型的可用提示词模版"}


def test_create_task_rejects_blank_task_input() -> None:
    response = client.post(
        "/api/vlm/tasks",
        json={
            "prompt_id": 9,
            "task_type": "label",
            "task_input": "   ",
            "remarks": "",
        },
    )

    assert response.status_code == 422


def test_update_task_maps_validated_payload(monkeypatch) -> None:
    def update_task(
        task_id: int,
        *,
        prompt_id: int,
        task_type: str,
        task_input: str,
        remarks: str,
        task_status: int,
    ):
        assert task_id == 25
        assert prompt_id == 9
        assert task_type == "label"
        assert task_input == "更新后的视频地址"
        assert remarks == "已复核"
        assert task_status == 2

    monkeypatch.setattr(
        vlm_service.repository,
        "update_task",
        update_task,
        raising=False,
    )
    response = client.put(
        "/api/vlm/tasks/25",
        json={
            "prompt_id": 9,
            "task_type": "label",
            "task_input": " 更新后的视频地址 ",
            "remarks": " 已复核 ",
            "task_status": 2,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"message": "任务更新成功"}


def test_update_task_rejects_invalid_status() -> None:
    response = client.put(
        "/api/vlm/tasks/25",
        json={
            "prompt_id": 9,
            "task_type": "label",
            "task_input": "视频地址",
            "remarks": "",
            "task_status": 3,
        },
    )

    assert response.status_code == 422


def test_update_task_returns_not_found(monkeypatch) -> None:
    def update_task(*_args, **_kwargs):
        raise VlmTaskNotFoundError("任务不存在")

    monkeypatch.setattr(
        vlm_service.repository,
        "update_task",
        update_task,
        raising=False,
    )
    response = client.put(
        "/api/vlm/tasks/404",
        json={
            "prompt_id": 9,
            "task_type": "label",
            "task_input": "视频地址",
            "remarks": "",
            "task_status": 0,
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "任务不存在"}


def test_delete_task_invokes_repository(monkeypatch) -> None:
    deleted = {}

    def delete_task(task_id: int):
        deleted["id"] = task_id

    monkeypatch.setattr(
        vlm_service.repository,
        "delete_task",
        delete_task,
        raising=False,
    )
    response = client.delete("/api/vlm/tasks/25")

    assert response.status_code == 200
    assert response.json() == {"message": "任务已删除"}
    assert deleted["id"] == 25


def test_delete_task_returns_not_found(monkeypatch) -> None:
    def delete_task(_task_id: int):
        raise VlmTaskNotFoundError("任务不存在")

    monkeypatch.setattr(
        vlm_service.repository,
        "delete_task",
        delete_task,
        raising=False,
    )
    response = client.delete("/api/vlm/tasks/404")

    assert response.status_code == 404
    assert response.json() == {"detail": "任务不存在"}


def test_prompt_list_maps_database_fields(monkeypatch) -> None:
    def list_prompts():
        return [
            {
                "id": 9,
                "title": "道路目标识别",
                "vlm_type": "label",
                "content": "识别画面中的车辆、行人与道路标识。",
                "is_closed": 0,
                "update_date": datetime(2026, 10, 22, 10, 30),
                "create_by": "admin",
            },
            {
                "id": 8,
                "title": "长尾场景挖掘",
                "vlm_type": "dig",
                "content": "发现低频高风险驾驶场景。",
                "is_closed": 1,
                "update_date": datetime(2026, 10, 21, 18, 0),
                "create_by": "tester",
            },
        ]

    monkeypatch.setattr(
        vlm_service.repository,
        "list_prompts",
        list_prompts,
        raising=False,
    )
    response = client.get("/api/vlm/prompts")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 9,
            "title": "道路目标识别",
            "vlm_type": "标注",
            "content": "识别画面中的车辆、行人与道路标识。",
            "is_closed": False,
            "update_date": "2026-10-22T10:30:00",
            "create_by": "admin",
        },
        {
            "id": 8,
            "title": "长尾场景挖掘",
            "vlm_type": "挖掘",
            "content": "发现低频高风险驾驶场景。",
            "is_closed": True,
            "update_date": "2026-10-21T18:00:00",
            "create_by": "tester",
        },
    ]


def test_prompt_list_returns_service_unavailable_for_repository_error(
    monkeypatch,
) -> None:
    def list_prompts():
        raise VlmRepositoryError("读取 VLM 提示词数据失败")

    monkeypatch.setattr(
        vlm_service.repository,
        "list_prompts",
        list_prompts,
        raising=False,
    )
    response = client.get("/api/vlm/prompts")

    assert response.status_code == 503
    assert response.json() == {"detail": "读取 VLM 提示词数据失败"}


def test_create_prompt_maps_validated_payload(monkeypatch) -> None:
    def create_prompt(**payload):
        assert payload == {
            "title": "道路目标识别",
            "vlm_type": "label",
            "content": "识别车辆与行人。",
            "is_closed": False,
            "create_by": "admin",
        }
        return 17

    monkeypatch.setattr(
        vlm_service.repository,
        "create_prompt",
        create_prompt,
        raising=False,
    )
    response = client.post(
        "/api/vlm/prompts",
        json={
            "title": " 道路目标识别 ",
            "vlm_type": "label",
            "content": " 识别车辆与行人。 ",
            "is_closed": False,
            "create_by": "admin",
        },
    )

    assert response.status_code == 201
    assert response.json() == {"id": 17, "message": "提示词创建成功"}


def test_update_prompt_maps_validated_payload(monkeypatch) -> None:
    def update_prompt(prompt_id: int, **payload):
        assert prompt_id == 17
        assert payload == {
            "title": "道路目标识别 V2",
            "vlm_type": "dig",
            "content": "发现长尾场景。",
            "is_closed": True,
        }

    monkeypatch.setattr(
        vlm_service.repository,
        "update_prompt",
        update_prompt,
        raising=False,
    )
    response = client.put(
        "/api/vlm/prompts/17",
        json={
            "title": " 道路目标识别 V2 ",
            "vlm_type": "dig",
            "content": " 发现长尾场景。 ",
            "is_closed": True,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"message": "提示词更新成功"}


def test_delete_prompt_uses_record_id(monkeypatch) -> None:
    deleted_ids: list[int] = []

    def delete_prompt(prompt_id: int):
        deleted_ids.append(prompt_id)

    monkeypatch.setattr(
        vlm_service.repository,
        "delete_prompt",
        delete_prompt,
        raising=False,
    )
    response = client.delete("/api/vlm/prompts/17")

    assert response.status_code == 200
    assert response.json() == {"message": "提示词已删除"}
    assert deleted_ids == [17]


def test_update_prompt_returns_not_found(monkeypatch) -> None:
    def update_prompt(*_args, **_kwargs):
        raise VlmPromptNotFoundError("提示词不存在")

    monkeypatch.setattr(
        vlm_service.repository,
        "update_prompt",
        update_prompt,
        raising=False,
    )
    response = client.put(
        "/api/vlm/prompts/404",
        json={
            "title": "不存在的提示词",
            "vlm_type": "label",
            "content": "测试内容",
            "is_closed": False,
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "提示词不存在"}
