from __future__ import annotations

from typing import Dict

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.repositories.vlm_task_repository import VlmRepositoryError
from app.schemas import VlmOverview, VlmTaskPage
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
    allow_methods=["GET"],
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
