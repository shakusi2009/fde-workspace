from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


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
    prompt_id: Optional[int] = None
    prompt_title: Optional[str] = None
    task_input: Optional[str] = None
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


class VlmTaskItem(BaseModel):
    id: int
    task_id: int
    model_id: str
    task_input: str
    total_tokens: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cached_tokens: Optional[int] = None
    task_status: Optional[int] = None
    output_text: Optional[str] = None


class VlmTaskItemPage(BaseModel):
    items: list[VlmTaskItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 10
    task_id: int


class VlmTaskExecutionContext(BaseModel):
    task_id: int
    prompt_id: int
    prompt_title: str
    prompt_content: str
    task_input: str


class VlmTaskExecuteRequest(BaseModel):
    model_id: str = Field(min_length=1, max_length=32)

    @field_validator("model_id", mode="before")
    @classmethod
    def strip_model_id(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class VlmTaskCreate(BaseModel):
    prompt_id: int = Field(gt=0)
    task_type: Literal["label", "dig"]
    task_input: str = Field(min_length=1)
    remarks: str = Field(default="", max_length=32)

    @field_validator("task_input", "remarks", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class VlmTaskUpdate(VlmTaskCreate):
    task_status: Literal[0, 1, 2]


class VlmTaskMutationResult(BaseModel):
    id: int
    message: str


class TosPrivateSignRequest(BaseModel):
    original_url: str = Field(min_length=1, max_length=1024)

    @field_validator("original_url", mode="before")
    @classmethod
    def strip_url(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class TosPrivateSignResponse(BaseModel):
    signed_url: str


class VlmPrompt(BaseModel):
    id: int
    title: str
    vlm_type: str
    content: str
    is_closed: bool
    update_date: datetime
    create_by: str


class VlmPromptUpdate(BaseModel):
    title: str = Field(min_length=1)
    vlm_type: Literal["label", "dig"]
    content: str = Field(min_length=1)
    is_closed: bool = False

    @field_validator("title", "content", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class VlmPromptCreate(VlmPromptUpdate):
    create_by: str = Field(min_length=1)

    @field_validator("create_by", mode="before")
    @classmethod
    def strip_creator(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class VlmPromptMutationResult(BaseModel):
    id: int
    message: str
