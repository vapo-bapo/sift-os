import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

EVENT_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*(?:\.[a-z][a-z0-9_-]*)+$")


class ProductEventIn(BaseModel):
    event_id: UUID
    event_type: str = Field(min_length=3, max_length=100)
    schema_version: int = Field(default=1, ge=1)
    occurred_at: datetime
    external_run_id: str | None = Field(default=None, min_length=1, max_length=200)
    status: str | None = Field(default=None, min_length=1, max_length=40)
    cost_cents: int = Field(default=0, ge=0)
    units: int = Field(default=0, ge=0)
    payload: dict[str, object] = Field(default_factory=dict)

    @field_validator("event_type")
    @classmethod
    def valid_event_type(cls, value: str) -> str:
        if EVENT_TYPE_PATTERN.fullmatch(value) is None:
            raise ValueError("event_type must be a lowercase namespaced identifier")
        return value

    @field_validator("occurred_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timezone-aware timestamp required")
        return value


class ProductEventAccepted(BaseModel):
    event_id: UUID
    duplicate: bool
    product_id: UUID
    run_id: UUID | None
