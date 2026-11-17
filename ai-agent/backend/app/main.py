from __future__ import annotations

from typing import Dict

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    DriverOption,
    VehicleAgentChatRequest,
    VehicleAgentChatResponse,
)
from app.services.vehicle_agent_service import (
    VehicleAgentConfigurationError,
    VehicleAgentExecutionError,
    VehicleAgentUpstreamError,
    vehicle_agent_service,
)


app = FastAPI(
    title="Stephen Vehicle Agent Service",
    version="1.0.0",
    docs_url="/api/vehicle-agent/docs",
    openapi_url="/api/vehicle-agent/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/vehicle-agent/health")
def health() -> Dict[str, str]:
    return {
        "status": "ok",
        "service": "Stephen Vehicle Agent Service",
    }


@app.get(
    "/api/vehicle-agent/drivers/options",
    response_model=list[DriverOption],
)
def list_driver_options(
    keyword: str = Query(default="", max_length=100),
) -> list[DriverOption]:
    try:
        return vehicle_agent_service.list_driver_options(keyword)
    except VehicleAgentUpstreamError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    "/api/vehicle-agent/chat",
    response_model=VehicleAgentChatResponse,
)
def chat(
    payload: VehicleAgentChatRequest,
) -> VehicleAgentChatResponse:
    try:
        return vehicle_agent_service.chat(payload)
    except VehicleAgentConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except VehicleAgentExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
