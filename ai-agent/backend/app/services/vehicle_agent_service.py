from __future__ import annotations

import os
import json
from contextvars import ContextVar
from typing import Annotated, Any, TypedDict

import httpx
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from openai import OpenAI, OpenAIError, PermissionDeniedError

from app.config import Settings, get_settings
from app.schemas import (
    DriverOption,
    VehicleAgentChatRequest,
    VehicleAgentChatResponse,
)


class VehicleAgentUpstreamError(RuntimeError):
    pass


class VehicleAgentConfigurationError(RuntimeError):
    pass


class VehicleAgentExecutionError(RuntimeError):
    pass


class VehicleAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    model_id: str
    system_prompt: str
    vehicle_model: str
    reasoning_summary: list[str]
    internet_used: bool
    sources: list[str]


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)


class VehicleAgentService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._active_model_id: ContextVar[str] = ContextVar(
            "vehicle_agent_model_id",
            default="",
        )
        self.tsp_service_url = os.getenv(
            "TSP_SERVICE_URL",
            "http://127.0.0.1:8002",
        ).rstrip("/")

        @tool
        def get_current_weather(city: str) -> str:
            """联网查询中国城市的当前天气和当日预报。

            Args:
                city: 要查询的中国城市名，例如“阿勒泰”或“北京”。
            """
            payload = self._request_json(
                "/api/agent-data/weather",
                {"city": city.strip().removesuffix("市")},
            )
            weather_log = payload.get("weather_log")
            if not isinstance(weather_log, str) or not weather_log.strip():
                raise VehicleAgentExecutionError(
                    "联网天气服务未返回有效数据"
                )
            return json.dumps(payload, ensure_ascii=False)

        @tool
        def doubao_web_search(query: str) -> str:
            """使用豆包搜索查询实时公开网络信息。

            适用于地点、商户、新闻、商品、行业动态、事实核验等需要
            联网搜索的问题。查询词应包含用户给出的地址、范围、类别
            和数量等完整约束。

            Args:
                query: 完整、具体的联网搜索查询词。
            """
            result = self._search_doubao(
                query=query,
                model_id=self._active_model_id.get(),
            )
            return json.dumps(result, ensure_ascii=False)

        self.tools: list[BaseTool] = [
            get_current_weather,
            doubao_web_search,
        ]
        self.tools_by_name = {item.name: item for item in self.tools}

        graph_builder = StateGraph(VehicleAgentState)
        graph_builder.add_node("agent", self._call_model)
        graph_builder.add_node("tools", self._execute_tools)
        graph_builder.add_edge(START, "agent")
        graph_builder.add_conditional_edges(
            "agent",
            self._route_after_model,
            {
                "tools": "tools",
                "end": END,
            },
        )
        graph_builder.add_edge("tools", "agent")
        self.graph = graph_builder.compile(checkpointer=InMemorySaver())

    @staticmethod
    def _route_after_model(state: VehicleAgentState) -> str:
        response = state["messages"][-1]
        if isinstance(response, AIMessage) and response.tool_calls:
            return "tools"
        return "end"

    def _execute_tools(self, state: VehicleAgentState) -> dict[str, Any]:
        response = state["messages"][-1]
        if not isinstance(response, AIMessage):
            raise VehicleAgentExecutionError("工具调用消息无效")

        results: list[ToolMessage] = []
        cities: list[str] = []
        search_queries: list[str] = []
        sources: list[str] = []
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            selected_tool = self.tools_by_name.get(tool_name)
            if selected_tool is None:
                raise VehicleAgentExecutionError(
                    f"不支持的联网工具：{tool_name}"
                )
            try:
                observation = selected_tool.invoke(tool_call["args"])
            except VehicleAgentExecutionError:
                raise
            except Exception as exc:
                raise VehicleAgentExecutionError(
                    f"联网工具执行失败：{tool_name}"
                ) from exc
            city = str(tool_call["args"].get("city", "")).strip()
            if tool_name == "get_current_weather":
                cities.append(city or "所选城市")
                sources.append("Open-Meteo（经 TSP 实时天气服务）")
            elif tool_name == "doubao_web_search":
                query = str(tool_call["args"].get("query", "")).strip()
                search_queries.append(query)
                try:
                    search_payload = json.loads(
                        _content_to_text(observation)
                    )
                except (TypeError, ValueError):
                    search_payload = {}
                for source in search_payload.get("sources", []):
                    if not isinstance(source, dict):
                        continue
                    title = str(source.get("title", "")).strip()
                    url = str(source.get("url", "")).strip()
                    if url:
                        sources.append(
                            f"{title}（{url}）" if title else url
                        )
            results.append(
                ToolMessage(
                    content=_content_to_text(observation),
                    tool_call_id=tool_call["id"],
                    name=tool_name,
                )
            )

        if search_queries and not cities:
            reasoning_summary = [
                f"模型选择豆包搜索工具：{'；'.join(search_queries)}",
                "豆包搜索已返回公开网络信息",
                f"结合{state['vehicle_model']}车辆上下文生成回答",
            ]
        elif cities and not search_queries:
            reasoning_summary = [
                f"模型选择联网天气工具：{'、'.join(cities)}",
                "工具已返回 Open-Meteo 实时天气",
                f"结合{state['vehicle_model']}车辆上下文生成回答",
            ]
        else:
            reasoning_summary = [
                "模型选择多个联网工具",
                "联网工具已返回实时信息",
                f"结合{state['vehicle_model']}车辆上下文生成回答",
            ]

        return {
            "messages": results,
            "reasoning_summary": reasoning_summary,
            "internet_used": True,
            "sources": list(dict.fromkeys(sources)),
        }

    @staticmethod
    def _extract_search_sources(payload: Any) -> list[dict[str, str]]:
        sources: list[dict[str, str]] = []

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                url = value.get("url")
                citation_type = value.get("type")
                if (
                    isinstance(url, str)
                    and url
                    and citation_type == "url_citation"
                ):
                    sources.append(
                        {
                            "title": str(value.get("title", "")).strip(),
                            "url": url,
                        }
                    )
                for nested in value.values():
                    visit(nested)
            elif isinstance(value, list):
                for nested in value:
                    visit(nested)

        visit(payload)
        unique: dict[str, dict[str, str]] = {}
        for source in sources:
            unique[source["url"]] = source
        return list(unique.values())

    def _search_doubao(
        self,
        *,
        query: str,
        model_id: str,
    ) -> dict[str, Any]:
        if not query.strip():
            raise VehicleAgentExecutionError("豆包搜索查询词不能为空")
        if not model_id:
            raise VehicleAgentExecutionError("豆包搜索缺少模型配置")

        client = OpenAI(
            api_key=self.settings.model_agent_api_key,
            base_url=self.settings.model_agent_base_url,
        )
        try:
            response = client.responses.create(
                model=model_id,
                input=query.strip(),
                tools=[
                    {
                        "type": "web_search",
                        "sources": ["doubao"],
                    }
                ],
            )
        except PermissionDeniedError as exc:
            raise VehicleAgentExecutionError(
                "豆包搜索服务未开通或当前 API Key 无权限，"
                "请在火山方舟“应用组件库 > 豆包搜索”中开通服务"
            ) from exc
        except OpenAIError as exc:
            raise VehicleAgentExecutionError(
                f"豆包搜索调用失败：{type(exc).__name__}"
            ) from exc

        answer = str(response.output_text or "").strip()
        if not answer:
            raise VehicleAgentExecutionError("豆包搜索未返回有效内容")
        payload = response.model_dump()
        return {
            "query": query.strip(),
            "model_id": model_id,
            "answer": answer,
            "sources": self._extract_search_sources(payload),
        }

    def _call_model(
        self,
        state: VehicleAgentState,
    ) -> dict[str, list[AIMessage]]:
        model = ChatOpenAI(
            model=state["model_id"],
            api_key=self.settings.model_agent_api_key,
            base_url=self.settings.model_agent_base_url,
            temperature=0,
        )
        model_with_tools = model.bind_tools(self.tools)
        response = model_with_tools.invoke(
            [
                SystemMessage(content=state["system_prompt"]),
                *state["messages"],
            ]
        )
        if not isinstance(response, AIMessage):
            raise VehicleAgentExecutionError("大模型未返回有效回答")
        update: dict[str, Any] = {"messages": [response]}
        if not response.tool_calls and not state["reasoning_summary"]:
            update["reasoning_summary"] = [
                "识别用户问题并读取所选车辆上下文",
                f"使用 {state['model_id']} 生成回答",
            ]
        return update

    @staticmethod
    def _system_prompt(driver: DriverOption) -> str:
        return "\n".join(
            [
                "你是专业、简洁的车端智能助理，请使用中文回答。",
                "请基于给定车辆上下文理解问题，但不要编造实时车况、控制结果或未提供的数据。",
                "如果用户要求执行车辆控制，明确说明你只能提供建议，不能声称操作已经完成。",
                "已提供 get_current_weather 联网工具。涉及当前天气、气温、降水、湿度等实时信息时必须调用该工具，禁止凭记忆回答。",
                "已提供 doubao_web_search 豆包搜索工具。涉及地点周边商户、新闻、商品、行业动态或其他实时公开网络信息时必须调用该工具。",
                f"用户未明确城市时，天气工具的 city 参数使用登记城市：{driver.registration_city}。",
                "收到工具结果后必须以工具数据为准，并说明实时数据具有时效性。",
                "车辆上下文：",
                f"- 车主：{driver.name}",
                f"- VIN：{driver.vin}",
                f"- 车型：{driver.vehicle_model}",
                f"- 登记城市：{driver.registration_city}",
                f"- 地址：{driver.address}",
            ]
        )

    def _request_json(
        self,
        path: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{self.tsp_service_url}{path}",
                params=params,
            )
            response.raise_for_status()
            return response.json()

    def list_driver_options(self, keyword: str) -> list[DriverOption]:
        try:
            payload = self._request_json(
                "/api/agent-data/drivers",
                {"page": 1, "keyword": keyword.strip()},
            )
            return [
                DriverOption.model_validate(item)
                for item in payload.get("items", [])
            ]
        except (
            httpx.HTTPError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise VehicleAgentUpstreamError(
                "车主数据服务暂不可用",
            ) from exc

    def chat(
        self,
        payload: VehicleAgentChatRequest,
    ) -> VehicleAgentChatResponse:
        if not self.settings.model_agent_configured:
            raise VehicleAgentConfigurationError("大模型 Agent 配置不完整")

        model_token = self._active_model_id.set(payload.model_id)
        try:
            try:
                result = self.graph.invoke(
                    {
                    "messages": [
                        {
                            "role": "user",
                            "content": payload.message,
                        }
                    ],
                    "model_id": payload.model_id,
                    "system_prompt": self._system_prompt(payload.driver),
                    "vehicle_model": payload.driver.vehicle_model,
                    "reasoning_summary": [],
                    "internet_used": False,
                    "sources": [],
                    },
                    {
                        "configurable": {
                            "thread_id": payload.session_id,
                        }
                    },
                )
            except VehicleAgentExecutionError:
                raise
            except Exception as exc:
                detail = str(exc).strip() or repr(exc)
                api_key = self.settings.model_agent_api_key.strip()
                if api_key:
                    detail = detail.replace(api_key, "***")
                raise VehicleAgentExecutionError(
                    f"大模型 Agent 执行失败（{type(exc).__name__}）：{detail}"
                ) from exc
        finally:
            self._active_model_id.reset(model_token)

        response = result["messages"][-1]
        if not isinstance(response, AIMessage):
            raise VehicleAgentExecutionError("大模型未返回有效回答")
        return VehicleAgentChatResponse(
            session_id=payload.session_id,
            model_id=payload.model_id,
            answer=_content_to_text(response.content),
            reasoning_summary=result["reasoning_summary"],
            internet_used=result["internet_used"],
            sources=result["sources"],
        )


vehicle_agent_service = VehicleAgentService(get_settings())
