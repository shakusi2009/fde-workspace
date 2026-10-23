from langchain_core.messages import AIMessage

import pytest

from app.config import Settings
from app.services.agent_service import (
    AgentConfigurationError,
    AgentExecutionError,
    VlmAgentService,
)


def test_agent_builds_single_role_graph_and_extracts_usage(monkeypatch) -> None:
    captured = {}

    class FakeChatModel:
        def __init__(self, **kwargs):
            captured["config"] = kwargs

        def invoke(self, messages):
            captured["messages"] = messages
            return AIMessage(
                content='{"is_lane_change": true}',
                usage_metadata={
                    "input_tokens": 120,
                    "output_tokens": 30,
                    "total_tokens": 150,
                    "input_token_details": {"cache_read": 20},
                },
            )

    monkeypatch.setattr(
        "app.services.agent_service.ChatOpenAI",
        FakeChatModel,
    )
    settings = Settings(
        _env_file=None,
        model_agent_api_key="test-key",
        model_agent_base_url="https://ark.example/api/v3",
    )
    service = VlmAgentService(settings)

    result = service.execute(
        prompt_content="你是自动驾驶视觉专家",
        task_input="分析该视频",
        model_id="ep-test-model",
    )

    assert captured["config"]["model"] == "ep-test-model"
    assert captured["config"]["api_key"] == "test-key"
    assert captured["config"]["base_url"] == "https://ark.example/api/v3"
    assert captured["messages"][0].type == "system"
    assert captured["messages"][0].content == "你是自动驾驶视觉专家"
    assert captured["messages"][1].type == "human"
    assert captured["messages"][1].content == "分析该视频"
    assert result.output_text == '{"is_lane_change": true}'
    assert result.total_tokens == 150
    assert result.input_tokens == 120
    assert result.output_tokens == 30
    assert result.cached_tokens == 20


def test_agent_rejects_missing_api_key() -> None:
    service = VlmAgentService(
        Settings(
            _env_file=None,
            model_agent_api_key="",
            model_agent_base_url="https://ark.example/api/v3",
        )
    )

    with pytest.raises(
        AgentConfigurationError,
        match="大模型 Agent 配置不完整",
    ):
        service.execute(
            prompt_content="系统提示词",
            task_input="任务输入",
            model_id="ep-test-model",
        )


def test_agent_preserves_specific_model_error(monkeypatch) -> None:
    class FailingChatModel:
        def __init__(self, **_kwargs):
            pass

        def invoke(self, _messages):
            raise RuntimeError("模型不存在或无访问权限")

    monkeypatch.setattr(
        "app.services.agent_service.ChatOpenAI",
        FailingChatModel,
    )
    service = VlmAgentService(
        Settings(
            _env_file=None,
            model_agent_api_key="test-key",
            model_agent_base_url="https://ark.example/api/v3",
        )
    )

    with pytest.raises(AgentExecutionError) as exc_info:
        service.execute(
            prompt_content="系统提示词",
            task_input="任务输入",
            model_id="missing-model",
        )

    assert str(exc_info.value) == (
        "大模型 Agent 执行失败（RuntimeError）：模型不存在或无访问权限"
    )
