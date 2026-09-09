from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.partners.models import PartnerStatus


class PartnerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    legal_name: str | None = Field(default=None, max_length=240)
    email: str | None = Field(default=None, max_length=320)
    domain: str | None = Field(default=None, max_length=253)
    owner_staff_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=4000)


class PartnerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    legal_name: str | None = Field(default=None, max_length=240)
    email: str | None = Field(default=None, max_length=320)
    domain: str | None = Field(default=None, max_length=253)
    owner_staff_id: UUID | None = None
    status: PartnerStatus | None = None
    notes: str | None = Field(default=None, max_length=4000)


class AgreementCreate(BaseModel):
    effective_from: datetime
    effective_to: datetime | None = None
    partner_share_bps: int = Field(default=2_000, ge=0, le=10_000)
    sift_share_bps: int = Field(default=8_000, ge=0, le=10_000)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    terms: dict[str, object] = Field(default_factory=dict)

    @field_validator("effective_from", "effective_to")
    @classmethod
    def timezone_required(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timezone-aware timestamp required")
        return value

    @model_validator(mode="after")
    def valid_split(self) -> "AgreementCreate":
        if self.partner_share_bps + self.sift_share_bps != 10_000:
            raise ValueError("revenue shares must total 10,000 basis points")
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be after effective_from")
        self.currency = self.currency.upper()
        return self


class PartnerClientCreate(BaseModel):
    external_client_id: UUID
    client_name: str = Field(min_length=1, max_length=240)
    attributed_at: datetime | None = None
    gross_revenue_cents: int = Field(ge=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)

    @field_validator("attributed_at")
    @classmethod
    def timezone_required(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timezone-aware timestamp required")
        return value


class AgreementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    partner_id: UUID
    version: int
    effective_from: datetime
    effective_to: datetime | None
    partner_share_bps: int
    sift_share_bps: int
    currency: str
    terms: dict[str, object]
    archived_at: datetime | None


class PartnerClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    partner_id: UUID
    agreement_id: UUID
    external_client_id: UUID
    client_name: str
    attributed_at: datetime
    gross_revenue_cents: int
    partner_share_cents: int
    sift_share_cents: int
    currency: str
    archived_at: datetime | None


class PartnerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    legal_name: str | None
    email: str | None
    domain: str | None
    owner_staff_id: UUID | None
    status: PartnerStatus
    notes: str | None
    signed_at: datetime | None
    activated_at: datetime | None
    first_customer_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PartnerMetrics(BaseModel):
    partners_total: int
    partners_active: int
    attributed_clients: int
    gross_revenue_cents: int
    partner_share_cents: int
    sift_share_cents: int
