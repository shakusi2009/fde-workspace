from __future__ import annotations

"TSP driver API schemas."

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class DriverPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=32)
    vin: str = Field(min_length=1, max_length=64)
    vehicle_model: str = Field(min_length=1, max_length=100)
    address: str = Field(default="", max_length=255)
    registration_city: str = Field(min_length=1, max_length=100)
    registration_date: date

    @field_validator(
        "name",
        "phone",
        "vin",
        "vehicle_model",
        "address",
        "registration_city",
        mode="before",
    )
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("vin")
    @classmethod
    def normalize_vin(cls, value: str) -> str:
        return value.upper()


class DriverCreate(DriverPayload):
    pass


class DriverUpdate(DriverPayload):
    pass


class Driver(DriverPayload):
    id: int
    create_time: datetime
    update_time: datetime


class DriverOption(BaseModel):
    id: int
    name: str
    vin: str
    vehicle_model: str


class DriverPage(BaseModel):
    items: list[Driver] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 10


class DriverMutationResult(BaseModel):
    id: int
    message: str
