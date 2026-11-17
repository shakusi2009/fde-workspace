import json

from langchain_core.messages import AIMessage, ToolMessage

import pytest

from app.config import Settings
from app.schemas import DriverOption, VehicleAgentChatRequest
from app.services.vehicle_agent_service import (
    VehicleAgentConfigurationError,
    VehicleAgentExecutionError,
    VehicleAgentService,
)


def chat_request(
    *,
    message: str,
    session_id: str = "session-1",
    model_id: str = "doubao-reasoning-test",
) -> VehicleAgentChatRequest:
    return VehicleAgentChatRequest(
        session_id=session_id,
        model_id=model_id,
        driver=DriverOption(
            id=7,
            name="王明明",
            vin="2T16BU270T7YTRALX",
            vehicle_model="坦克 500",
            address="新疆维吾尔自治区阿勒泰市",
            registration_city="阿勒泰",
        ),
        message=message,
    )


def configured_settings() -> Settings:
    return Settings(
        _env_file=None,
        model_agent_api_key="test-secret-key",
        model_agent_base_url="https://ark.example/api/v3",
    )


def test_chat_uses_selected_model_and_vehicle_context(monkeypatch) -> None:
    captured: dict = {}

    class FakeChatModel:
        def __init__(self, **kwargs):
            captured["config"] = kwargs

        def bind_tools(self, tools):
            captured["tools"] = tools
            return self

        def invoke(self, messages):
            captured["messages"] = messages
            return AIMessage(content="车辆状态正常")

    monkeypatch.setattr(
        "app.services.vehicle_agent_service.ChatOpenAI",
        FakeChatModel,
    )
    service = VehicleAgentService(configured_settings())

    result = service.chat(chat_request(message="检查车辆状态"))

    assert captured["config"] == {
        "model": "doubao-reasoning-test",
        "api_key": "test-secret-key",
        "base_url": "https://ark.example/api/v3",
        "temperature": 0,
    }
    assert captured["messages"][0].type == "system"
    system_prompt = captured["messages"][0].content
    assert "王明明" in system_prompt
    assert "2T16BU270T7YTRALX" in system_prompt
    assert "坦克 500" in system_prompt
    assert "阿勒泰" in system_prompt
    assert captured["messages"][-1].content == "检查车辆状态"
    assert captured["tools"][0].name == "get_current_weather"
    assert result.answer == "车辆状态正常"
    assert result.session_id == "session-1"
    assert result.model_id == "doubao-reasoning-test"
    assert result.internet_used is False
    assert result.sources == []
    assert result.reasoning_summary == [
        "识别用户问题并读取所选车辆上下文",
        "使用 doubao-reasoning-test 生成回答",
    ]


def test_chat_queries_real_weather_and_injects_result(monkeypatch) -> None:
    captured: dict = {}

    class FakeChatModel:
        def __init__(self, **_kwargs):
            pass

        def bind_tools(self, tools):
            captured["tools"] = tools
            return self

        def invoke(self, messages):
            captured.setdefault("invocations", []).append(list(messages))
            if not any(isinstance(message, ToolMessage) for message in messages):
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "get_current_weather",
                            "args": {"city": "阿勒泰"},
                            "id": "weather-call-1",
                            "type": "tool_call",
                        }
                    ],
                )
            return AIMessage(content="阿勒泰当前小雪，建议出发前除霜。")

    def fake_request(path: str, params: dict) -> dict:
        captured["weather_request"] = (path, params)
        return {
            "city": "阿勒泰",
            "date": "2026-10-29",
            "current_temperature": -6.2,
            "current_humidity": 82,
            "current_weather": "小雪",
            "max_temperature": -1.0,
            "min_temperature": -12.0,
            "daily_weather": "小雪",
            "snowfall_cm": 1.4,
            "rain_mm": 0.0,
            "precipitation_probability": 80,
            "freeze_warning": "最低温-12.0℃，有道路结冰风险",
            "recommendation": "除冰除霜、暖风预热",
            "weather_log": "阿勒泰实时天气：-6.2℃，小雪",
        }

    monkeypatch.setattr(
        "app.services.vehicle_agent_service.ChatOpenAI",
        FakeChatModel,
    )
    service = VehicleAgentService(configured_settings())
    monkeypatch.setattr(service, "_request_json", fake_request)

    result = service.chat(
        chat_request(message="查询阿勒泰，当前天气")
    )

    assert captured["weather_request"] == (
        "/api/agent-data/weather",
        {"city": "阿勒泰"},
    )
    assert captured["tools"][0].name == "get_current_weather"
    tool_messages = [
        message
        for message in captured["invocations"][1]
        if isinstance(message, ToolMessage)
    ]
    assert len(tool_messages) == 1
    assert "阿勒泰实时天气：-6.2℃，小雪" in tool_messages[0].content
    assert result.internet_used is True
    assert result.sources == ["Open-Meteo（经 TSP 实时天气服务）"]
    assert result.reasoning_summary == [
        "模型选择联网天气工具：阿勒泰",
        "工具已返回 Open-Meteo 实时天气",
        "结合坦克 500车辆上下文生成回答",
    ]


def test_weather_tool_uses_model_selected_driver_city(monkeypatch) -> None:
    captured: dict = {}

    class FakeChatModel:
        def __init__(self, **_kwargs):
            pass

        def bind_tools(self, _tools):
            return self

        def invoke(self, messages):
            if not any(isinstance(message, ToolMessage) for message in messages):
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "get_current_weather",
                            "args": {"city": "阿勒泰"},
                            "id": "weather-call-2",
                            "type": "tool_call",
                        }
                    ],
                )
            return AIMessage(content="当前天气回答")

    def fake_request(_path: str, params: dict) -> dict:
        captured["city"] = params["city"]
        return {"weather_log": "天气数据"}

    monkeypatch.setattr(
        "app.services.vehicle_agent_service.ChatOpenAI",
        FakeChatModel,
    )
    service = VehicleAgentService(configured_settings())
    monkeypatch.setattr(service, "_request_json", fake_request)

    service.chat(chat_request(message="今天会下雪吗？"))

    assert captured["city"] == "阿勒泰"


def test_chat_uses_doubao_search_tool_and_returns_sources(monkeypatch) -> None:
    captured: dict = {}

    class FakeChatModel:
        def __init__(self, **_kwargs):
            pass

        def bind_tools(self, tools):
            captured["tool_names"] = [item.name for item in tools]
            return self

        def invoke(self, messages):
            if not any(isinstance(message, ToolMessage) for message in messages):
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "doubao_web_search",
                            "args": {
                                "query": (
                                    "北京火山引擎总部1号楼 "
                                    "附近一公里 top5 火锅店"
                                )
                            },
                            "id": "search-call-1",
                            "type": "tool_call",
                        }
                    ],
                )
            captured["tool_message"] = next(
                message
                for message in messages
                if isinstance(message, ToolMessage)
            )
            return AIMessage(content="附近火锅店搜索结果")

    monkeypatch.setattr(
        "app.services.vehicle_agent_service.ChatOpenAI",
        FakeChatModel,
    )
    service = VehicleAgentService(configured_settings())
    monkeypatch.setattr(
        service,
        "_search_doubao",
        lambda query, model_id: {
            "answer": "搜索到5家火锅店",
            "sources": [
                {
                    "title": "商户列表",
                    "url": "https://example.com/poi",
                }
            ],
            "query": query,
            "model_id": model_id,
        },
    )

    result = service.chat(
        chat_request(
            message=(
                "帮我查下：北京火山引擎总部1号楼，"
                "附近一公里内的top5火锅店"
            )
        )
    )

    assert captured["tool_names"] == [
        "get_current_weather",
        "doubao_web_search",
    ]
    tool_payload = json.loads(captured["tool_message"].content)
    assert tool_payload["model_id"] == "doubao-reasoning-test"
    assert "火锅店" in tool_payload["query"]
    assert result.internet_used is True
    assert result.sources == ["商户列表（https://example.com/poi）"]
    assert result.reasoning_summary[0].startswith("模型选择豆包搜索工具")


def test_doubao_search_source_extraction_deduplicates_urls() -> None:
    sources = VehicleAgentService._extract_search_sources(
        {
            "output": [
                {
                    "content": [
                        {
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "title": "来源 A",
                                    "url": "https://example.com/a",
                                },
                                {
                                    "type": "url_citation",
                                    "title": "来源 A",
                                    "url": "https://example.com/a",
                                },
                            ]
                        }
                    ]
                }
            ]
        }
    )

    assert sources == [
        {
            "title": "来源 A",
            "url": "https://example.com/a",
        }
    ]


def test_normal_turn_after_weather_resets_internet_metadata(monkeypatch) -> None:
    calls = {"weather": 0}

    class FakeChatModel:
        def __init__(self, **_kwargs):
            pass

        def bind_tools(self, _tools):
            return self

        def invoke(self, messages):
            latest_human = next(
                (
                    message.content
                    for message in reversed(messages)
                    if message.type == "human"
                ),
                "",
            )
            has_tool_result = any(
                isinstance(message, ToolMessage)
                for message in messages
            )
            if "天气" in latest_human and not has_tool_result:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "get_current_weather",
                            "args": {"city": "阿勒泰"},
                            "id": "weather-call-3",
                            "type": "tool_call",
                        }
                    ],
                )
            return AIMessage(content="回答")

    def fake_request(_path: str, _params: dict) -> dict:
        calls["weather"] += 1
        return {"weather_log": "天气数据"}

    monkeypatch.setattr(
        "app.services.vehicle_agent_service.ChatOpenAI",
        FakeChatModel,
    )
    service = VehicleAgentService(configured_settings())
    monkeypatch.setattr(service, "_request_json", fake_request)

    service.chat(chat_request(message="当前天气怎么样？"))
    result = service.chat(chat_request(message="介绍一下我的车型"))

    assert calls["weather"] == 1
    assert result.internet_used is False
    assert result.sources == []
    assert result.reasoning_summary == [
        "识别用户问题并读取所选车辆上下文",
        "使用 doubao-reasoning-test 生成回答",
    ]


def test_chat_preserves_messages_within_session(monkeypatch) -> None:
    invocations: list[list] = []

    class FakeChatModel:
        def __init__(self, **_kwargs):
            pass

        def bind_tools(self, _tools):
            return self

        def invoke(self, messages):
            invocations.append(list(messages))
            return AIMessage(content=f"回答-{len(invocations)}")

    monkeypatch.setattr(
        "app.services.vehicle_agent_service.ChatOpenAI",
        FakeChatModel,
    )
    service = VehicleAgentService(configured_settings())

    service.chat(chat_request(message="第一轮问题"))
    result = service.chat(chat_request(message="第二轮问题"))

    assert [message.content for message in invocations[1]] == [
        invocations[1][0].content,
        "第一轮问题",
        "回答-1",
        "第二轮问题",
    ]
    assert invocations[1][0].type == "system"
    assert result.answer == "回答-2"


def test_chat_rejects_missing_model_configuration() -> None:
    service = VehicleAgentService(
        Settings(
            _env_file=None,
            model_agent_api_key="",
            model_agent_base_url="https://ark.example/api/v3",
        )
    )

    with pytest.raises(
        VehicleAgentConfigurationError,
        match="大模型 Agent 配置不完整",
    ):
        service.chat(chat_request(message="检查车辆状态"))


def test_chat_redacts_api_key_from_model_error(monkeypatch) -> None:
    class FailingChatModel:
        def __init__(self, **_kwargs):
            pass

        def bind_tools(self, _tools):
            return self

        def invoke(self, _messages):
            raise RuntimeError("authorization failed: test-secret-key")

    monkeypatch.setattr(
        "app.services.vehicle_agent_service.ChatOpenAI",
        FailingChatModel,
    )
    service = VehicleAgentService(configured_settings())

    with pytest.raises(VehicleAgentExecutionError) as exc_info:
        service.chat(chat_request(message="检查车辆状态"))

    assert "test-secret-key" not in str(exc_info.value)
    assert "***" in str(exc_info.value)
