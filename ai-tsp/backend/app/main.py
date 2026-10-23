from __future__ import annotations

from typing import Dict

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.driver_schemas import (
    DriverCreate,
    DriverMutationResult,
    DriverPage,
    DriverUpdate,
)
from app.repositories.driver_repository import (
    DriverNotFoundError,
    DriverRepositoryError,
    DriverVinConflictError,
)
from app.services.driver_service import driver_service


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


@app.get(f"{settings.api_prefix}/drivers", response_model=DriverPage)
def list_drivers(
    page: int = Query(default=1, ge=1),
    keyword: str = Query(default="", max_length=100),
) -> DriverPage:
    try:
        return driver_service.list_drivers(page=page, keyword=keyword)
    except DriverRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    f"{settings.api_prefix}/drivers",
    response_model=DriverMutationResult,
    status_code=201,
)
def create_driver(payload: DriverCreate) -> DriverMutationResult:
    try:
        driver_id = driver_service.create_driver(payload)
        return DriverMutationResult(id=driver_id, message="车主创建成功")
    except DriverVinConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DriverRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.put(f"{settings.api_prefix}/drivers/{{driver_id}}")
def update_driver(
    driver_id: int,
    payload: DriverUpdate,
) -> Dict[str, str]:
    try:
        driver_service.update_driver(driver_id, payload)
        return {"message": "车主信息已更新"}
    except DriverNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DriverVinConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DriverRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.delete(f"{settings.api_prefix}/drivers/{{driver_id}}")
def delete_driver(driver_id: int) -> Dict[str, str]:
    try:
        driver_service.delete_driver(driver_id)
        return {"message": "车主已删除"}
    except DriverNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DriverRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
