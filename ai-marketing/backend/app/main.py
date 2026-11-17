from __future__ import annotations

from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    SalesFilterOptions,
    SalesPeriodsResponse,
    VehicleSalesRanking,
)
from app.services.dongchedi_service import (
    DongchediEmptyResultError,
    DongchediUpstreamError,
    dongchedi_service,
)


app = FastAPI(
    title="Stephen Marketing AI Service",
    version="0.1.0",
    docs_url="/api/marketing-ai/docs",
    openapi_url="/api/marketing-ai/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/marketing-ai/health")
def health() -> Dict[str, str]:
    return {
        "status": "ok",
        "service": "Stephen Marketing AI Service",
    }


@app.get(
    "/api/marketing-ai/public-insight/sales/periods",
    response_model=SalesPeriodsResponse,
)
def get_vehicle_sales_periods() -> SalesPeriodsResponse:
    try:
        return dongchedi_service.get_available_periods()
    except DongchediEmptyResultError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DongchediUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get(
    "/api/marketing-ai/public-insight/sales/filters",
    response_model=SalesFilterOptions,
)
def get_vehicle_sales_filters(
    year: int = Query(ge=2020, le=2100),
    month: int = Query(ge=1, le=12),
) -> SalesFilterOptions:
    try:
        return dongchedi_service.get_filter_options(
            year=year,
            month=month,
        )
    except DongchediUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get(
    "/api/marketing-ai/public-insight/sales",
    response_model=VehicleSalesRanking,
)
def get_vehicle_sales_ranking(
    year: int = Query(ge=2020, le=2100),
    month: int = Query(ge=1, le=12),
    vehicle_type: str = Query(
        default="all",
        pattern="^(all|sedan|suv|mpv|new-energy)$",
    ),
    level: str = Query(default="", max_length=32),
    energy_type: str = Query(default="", pattern="^$|^[123]$"),
    manufacturer: str = Query(
        default="",
        pattern="^$|^(自主|合资|进口)$",
    ),
    brand_id: Optional[int] = Query(default=None, ge=1),
) -> VehicleSalesRanking:
    try:
        return dongchedi_service.get_sales_ranking(
            year=year,
            month=month,
            vehicle_type=vehicle_type,
            level=level,
            energy_type=energy_type,
            manufacturer=manufacturer,
            brand_id=brand_id,
        )
    except DongchediEmptyResultError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DongchediUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
