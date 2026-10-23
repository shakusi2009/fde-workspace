from __future__ import annotations

from typing import Dict

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.repositories.vlm_task_repository import (
    VlmPromptNotFoundError,
    VlmRepositoryError,
    VlmTaskNotFoundError,
    VlmTaskExecutionUnavailableError,
    VlmTaskPromptUnavailableError,
)
from app.schemas import (
    TosPrivateSignRequest,
    TosPrivateSignResponse,
    VlmOverview,
    VlmPrompt,
    VlmPromptCreate,
    VlmPromptMutationResult,
    VlmPromptUpdate,
    VlmTaskCreate,
    VlmTaskExecuteRequest,
    VlmTaskExecutionContext,
    VlmTaskItem,
    VlmTaskItemPage,
    VlmTaskMutationResult,
    VlmTaskPage,
    VlmTaskUpdate,
)
from app.services.agent_service import AgentConfigurationError
from app.services.tos_service import (
    TosConfigurationError,
    TosSigningError,
    TosUrlError,
    tos_signing_service,
)
from app.services.vlm_service import vlm_service


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url=f"{settings.api_prefix}/docs",
    openapi_url=f"{settings.api_prefix}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.get(f"{settings.api_prefix}/health")
def health() -> Dict[str, object]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "rds_configured": settings.rds_configured,
    }


@app.get(f"{settings.api_prefix}/overview", response_model=VlmOverview)
def get_overview() -> VlmOverview:
    try:
        return vlm_service.get_overview()
    except VlmRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get(f"{settings.api_prefix}/tasks", response_model=VlmTaskPage)
def list_tasks(
    page: int = Query(default=1, ge=1),
) -> VlmTaskPage:
    try:
        return vlm_service.list_tasks(page=page)
    except VlmRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get(
    f"{settings.api_prefix}/tasks/{{task_id}}/items",
    response_model=VlmTaskItemPage,
)
def list_task_items(
    task_id: int,
    page: int = Query(default=1, ge=1),
) -> VlmTaskItemPage:
    try:
        return vlm_service.list_task_items(task_id=task_id, page=page)
    except VlmTaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VlmRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get(
    f"{settings.api_prefix}/tasks/{{task_id}}/execution-context",
    response_model=VlmTaskExecutionContext,
)
def get_task_execution_context(task_id: int) -> VlmTaskExecutionContext:
    try:
        return vlm_service.get_task_execution_context(task_id)
    except VlmTaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VlmTaskExecutionUnavailableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except VlmRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    f"{settings.api_prefix}/tasks/{{task_id}}/executions",
    response_model=VlmTaskItem,
    status_code=201,
)
def execute_task(
    task_id: int,
    payload: VlmTaskExecuteRequest,
) -> VlmTaskItem:
    try:
        return vlm_service.execute_task(task_id, payload.model_id)
    except VlmTaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VlmTaskExecutionUnavailableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AgentConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except VlmRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    f"{settings.api_prefix}/tasks",
    response_model=VlmTaskMutationResult,
    status_code=201,
)
def create_task(payload: VlmTaskCreate) -> VlmTaskMutationResult:
    try:
        task_id = vlm_service.create_task(payload)
        return VlmTaskMutationResult(id=task_id, message="任务创建成功")
    except VlmTaskPromptUnavailableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except VlmRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.put(f"{settings.api_prefix}/tasks/{{task_id}}")
def update_task(task_id: int, payload: VlmTaskUpdate) -> Dict[str, str]:
    try:
        vlm_service.update_task(task_id, payload)
        return {"message": "任务更新成功"}
    except VlmTaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VlmTaskPromptUnavailableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except VlmRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.delete(f"{settings.api_prefix}/tasks/{{task_id}}")
def delete_task(task_id: int) -> Dict[str, str]:
    try:
        vlm_service.delete_task(task_id)
        return {"message": "任务已删除"}
    except VlmTaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VlmRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    f"{settings.api_prefix}/tos/private-sign",
    response_model=TosPrivateSignResponse,
)
def generate_tos_private_sign(
    payload: TosPrivateSignRequest,
) -> TosPrivateSignResponse:
    try:
        signed_url = tos_signing_service.generate_private_signed_url(
            payload.original_url
        )
        return TosPrivateSignResponse(signed_url=signed_url)
    except TosUrlError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TosConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TosSigningError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get(f"{settings.api_prefix}/prompts", response_model=list[VlmPrompt])
def list_prompts() -> list[VlmPrompt]:
    try:
        return vlm_service.list_prompts()
    except VlmRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    f"{settings.api_prefix}/prompts",
    response_model=VlmPromptMutationResult,
    status_code=201,
)
def create_prompt(payload: VlmPromptCreate) -> VlmPromptMutationResult:
    try:
        prompt_id = vlm_service.create_prompt(payload)
        return VlmPromptMutationResult(id=prompt_id, message="提示词创建成功")
    except VlmRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.put(f"{settings.api_prefix}/prompts/{{prompt_id}}")
def update_prompt(prompt_id: int, payload: VlmPromptUpdate) -> Dict[str, str]:
    try:
        vlm_service.update_prompt(prompt_id, payload)
        return {"message": "提示词更新成功"}
    except VlmPromptNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VlmRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.delete(f"{settings.api_prefix}/prompts/{{prompt_id}}")
def delete_prompt(prompt_id: int) -> Dict[str, str]:
    try:
        vlm_service.delete_prompt(prompt_id)
        return {"message": "提示词已删除"}
    except VlmPromptNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VlmRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
