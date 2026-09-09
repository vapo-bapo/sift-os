from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.finance.models import FinancialEntryType


class FinancialEntryCreate(BaseModel):
    date: Date
    entry_type: FinancialEntryType
    category: str = Field(min_length=1, max_length=120)
    amount_cents: int = Field(gt=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    account_id: UUID | None = None
    partner_id: UUID | None = None
    product_id: UUID | None = None
    recurring: bool = False
    source: str | None = Field(default=None, max_length=160)
    note: str | None = None


class FinancialEntryPatch(BaseModel):
    date: Date | None = None
    entry_type: FinancialEntryType | None = None
    category: str | None = Field(default=None, min_length=1, max_length=120)
    amount_cents: int | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    account_id: UUID | None = None
    partner_id: UUID | None = None
    product_id: UUID | None = None
    recurring: bool | None = None
    source: str | None = Field(default=None, max_length=160)
    note: str | None = None
    archive: bool = False


class FinancialEntryResponse(FinancialEntryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_by_id: UUID | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class FinancialEntryList(BaseModel):
    items: list[FinancialEntryResponse]
    total: int
    page: int
    page_size: int


class FinancialSnapshotCreate(BaseModel):
    date: Date
    cash_cents: int
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    note: str | None = None


class FinancialSnapshotResponse(FinancialSnapshotCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_by_id: UUID | None
    created_at: datetime
    updated_at: datetime


class FinanceMetrics(BaseModel):
    cash_cents: int
    burn_cents: int
    mrr_cents: int
    arr_cents: int
    contracted_revenue_cents: int
    pipeline_revenue_cents: int
    weighted_pipeline_cents: int
    revenue_mtd_cents: int
    cost_mtd_cents: int
    api_cloud_cost_cents: int
    gross_margin_cents: int
    partner_commission_accrued_cents: int
    partner_commission_paid_cents: int
    partner_commission_payable_cents: int
