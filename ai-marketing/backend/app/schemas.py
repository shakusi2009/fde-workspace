from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class VehicleSalesRankItem(BaseModel):
    rank: int
    series_id: int
    series_name: str
    brand_name: str
    manufacturer: str
    sales: int
    previous_rank: Optional[int]
    image: str
    price: str


class SalesFilterOption(BaseModel):
    value: str
    label: str


class SalesBrandOption(BaseModel):
    id: int
    name: str


class SalesFilterOptions(BaseModel):
    vehicle_types: list[SalesFilterOption]
    energy_types: list[SalesFilterOption]
    manufacturers: list[SalesFilterOption]
    brands: list[SalesBrandOption]


class VehicleSalesRanking(BaseModel):
    year: int
    month: int
    period: str
    source_name: str
    source_url: str
    source_note: str
    filters: dict[str, str]
    items: list[VehicleSalesRankItem]


class SalesPeriod(BaseModel):
    year: int
    month: int
    period: str
    label: str


class SalesPeriodsResponse(BaseModel):
    source_name: str
    periods: list[SalesPeriod]
