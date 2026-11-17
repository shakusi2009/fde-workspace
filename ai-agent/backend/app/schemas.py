from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class DriverOption(BaseModel):
    id: int
    name: str
    vin: str
    vehicle_model: str
    address: str
    registration_city: str


class VehicleAgentChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=255)
    model_id: str = Field(min_length=1, max_length=255)
    driver: DriverOption
    message: str = Field(min_length=1, max_length=1000)

    @field_validator("session_id", "model_id", "message", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class VehicleAgentChatResponse(BaseModel):
    session_id: str
    model_id: str
    answer: str
    reasoning_summary: list[str]
    internet_used: bool
    sources: list[str]
