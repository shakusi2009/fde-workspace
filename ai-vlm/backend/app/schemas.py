from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TrendPoint(BaseModel):
    label: str
    value: int = 0


class VlmOverview(BaseModel):
    task_total: int = 0
    overall_accuracy: Optional[float] = None
    token_total: int = 0
    task_trend: list[TrendPoint] = Field(default_factory=list)
    token_trend: list[TrendPoint] = Field(default_factory=list)
    data_status: str = "pending"


class VlmTask(BaseModel):
    sequence: int
    task_type: str
    created_at: datetime
    token_usage: int
    accuracy: Optional[float] = None
    remark: str = ""
    task_status: int
    updated_at: Optional[datetime] = None


class VlmTaskPage(BaseModel):
    items: list[VlmTask] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 10
