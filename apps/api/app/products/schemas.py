from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    active: bool


class CredentialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def timezone_required(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timezone-aware timestamp required")
        return value


class CredentialIssued(BaseModel):
    id: UUID
    product_id: UUID
    name: str
    token: str
    created_at: datetime
    expires_at: datetime | None


class CredentialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    name: str
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None


class ProductMetricRead(BaseModel):
    product_id: UUID
    code: str
    runs_total: int
    runs_running: int
    runs_succeeded: int
    runs_failed: int
    events_total: int
    cost_cents: int
    units: int
