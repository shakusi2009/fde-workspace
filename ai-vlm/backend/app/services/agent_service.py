from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph

from app.config import Settings, get_settings


class AgentError(RuntimeError):
    pass


class AgentConfigurationError(AgentError):
    pass


class AgentExecutionError(AgentError):
    pass


@dataclass(frozen=True)
class AgentExecutionResult:
    output_text: str
    total_tokens: Optional[int]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    cached_tokens: Optional[int]


def _as_optional_int(value: object) -> Optional[int]:
    return int(value) if isinstance(value, (int, float)) else None


def _extract_usage(message: AIMessage) -> tuple[
    Optional[int],
    Optional[int],
    Optional[int],
    Optional[int],
]:
    usage = message.usage_metadata or {}
    response_usage = message.response_metadata.get("token_usage", {})
    if not isinstance(response_usage, dict):
        response_usage = {}

    input_tokens = _as_optional_int(
        usage.get("input_tokens", response_usage.get("prompt_tokens"))
    )
    output_tokens = _as_optional_int(
        usage.get("output_tokens", response_usage.get("completion_tokens"))
    )
    total_tokens = _as_optional_int(
        usage.get("total_tokens", response_usage.get("total_tokens"))
    )

    input_details = usage.get("input_token_details", {})
    if not isinstance(input_details, dict):
        input_details = {}
    prompt_details = response_usage.get("prompt_tokens_details", {})
    if not isinstance(prompt_details, dict):
        prompt_details = {}
    cached_tokens = _as_optional_int(
        input_details.get("cache_read", prompt_details.get("cached_tokens"))
    )
    return total_tokens, input_tokens, output_tokens, cached_tokens


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)


class VlmAgentService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def execute(
        self,
        *,
        prompt_content: str,
        task_input: str,
        model_id: str,
    ) -> AgentExecutionResult:
        if not self.settings.model_agent_configured:
            raise AgentConfigurationError("大模型 Agent 配置不完整")

        model = ChatOpenAI(
            model=model_id,
            api_key=self.settings.model_agent_api_key,
            base_url=self.settings.model_agent_base_url,
            temperature=0,
        )

        def call_model(state: MessagesState) -> dict[str, list[AIMessage]]:
            response = model.invoke(state["messages"])
            if not isinstance(response, AIMessage):
                raise AgentExecutionError("大模型 Agent 未返回有效文本")
            return {"messages": [response]}

        graph_builder = StateGraph(MessagesState)
        graph_builder.add_node("agent", call_model)
        graph_builder.add_edge(START, "agent")
        graph_builder.add_edge("agent", END)
        graph = graph_builder.compile()

        try:
            result = graph.invoke(
                {
                    "messages": [
                        SystemMessage(content=prompt_content),
                        HumanMessage(content=task_input),
                    ]
                }
            )
        except AgentExecutionError:
            raise
        except Exception as exc:
            detail = str(exc).strip() or repr(exc)
            api_key = self.settings.model_agent_api_key.strip()
            if api_key:
                detail = detail.replace(api_key, "***")
            raise AgentExecutionError(
                f"大模型 Agent 执行失败（{type(exc).__name__}）：{detail}"
            ) from exc

        response = result["messages"][-1]
        if not isinstance(response, AIMessage):
            raise AgentExecutionError("大模型 Agent 未返回有效文本")
        total, input_count, output_count, cached = _extract_usage(response)
        return AgentExecutionResult(
            output_text=_content_to_text(response.content),
            total_tokens=total,
            input_tokens=input_count,
            output_tokens=output_count,
            cached_tokens=cached,
        )


vlm_agent_service = VlmAgentService(get_settings())
