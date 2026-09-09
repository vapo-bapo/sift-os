from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.crm.models import (
    AccountStatus,
    AccountType,
    ActivityType,
    OpportunityChannel,
    OpportunityStage,
    OpportunityStatus,
    PreferredChannel,
)


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


class AccountCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=200)
    domain: str | None = Field(default=None, max_length=253)
    website: str | None = Field(default=None, max_length=500)
    industry: str | None = Field(default=None, max_length=100)
    company_size: str | None = Field(default=None, max_length=50)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    city: str | None = Field(default=None, max_length=100)
    account_type: AccountType = AccountType.DIRECT_PROSPECT
    source: str | None = Field(default=None, max_length=100)
    owner_id: UUID | None = None
    status: AccountStatus = AccountStatus.NEW
    lead_score: int = Field(default=0, ge=0, le=100)
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name cannot be blank")
        return value


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    domain: str | None = Field(default=None, max_length=253)
    website: str | None = Field(default=None, max_length=500)
    industry: str | None = Field(default=None, max_length=100)
    company_size: str | None = Field(default=None, max_length=50)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    city: str | None = Field(default=None, max_length=100)
    account_type: AccountType | None = None
    source: str | None = Field(default=None, max_length=100)
    owner_id: UUID | None = None
    status: AccountStatus | None = None
    lead_score: int | None = Field(default=None, ge=0, le=100)
    notes: str | None = None


class AccountResponse(AccountCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class ContactCreate(BaseModel):
    account_id: UUID
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    linkedin_url: str | None = Field(default=None, max_length=500)
    preferred_channel: PreferredChannel | None = None
    is_decision_maker: bool = False
    notes: str | None = None


class ContactUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    linkedin_url: str | None = Field(default=None, max_length=500)
    preferred_channel: PreferredChannel | None = None
    is_decision_maker: bool | None = None
    notes: str | None = None


class ContactResponse(ContactCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class OpportunityCreate(BaseModel):
    account_id: UUID
    primary_contact_id: UUID | None = None
    owner_id: UUID | None = None
    stage: OpportunityStage = OpportunityStage.PROSPECT
    status: OpportunityStatus = OpportunityStatus.OPEN
    estimated_value_cents: int = Field(default=0, ge=0)
    probability: int = Field(default=0, ge=0, le=100)
    expected_close_date: date | None = None
    source: str | None = Field(default=None, max_length=100)
    channel: OpportunityChannel = OpportunityChannel.DIRECT_SALES
    interested_products: list[str] = Field(default_factory=list)
    next_action: str | None = Field(default=None, max_length=500)
    next_action_at: datetime | None = None
    lost_reason: str | None = None

    @property
    def weighted_value_cents(self) -> int:
        return self.estimated_value_cents * self.probability // 100


class OpportunityUpdate(BaseModel):
    primary_contact_id: UUID | None = None
    estimated_value_cents: int | None = Field(default=None, ge=0)
    probability: int | None = Field(default=None, ge=0, le=100)
    expected_close_date: date | None = None
    source: str | None = Field(default=None, max_length=100)
    channel: OpportunityChannel | None = None
    interested_products: list[str] | None = None
    next_action: str | None = Field(default=None, max_length=500)
    next_action_at: datetime | None = None
    lost_reason: str | None = None


class OpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    account_id: UUID
    primary_contact_id: UUID | None
    owner_id: UUID
    stage: OpportunityStage
    status: OpportunityStatus
    estimated_value_cents: int
    weighted_value_cents: int
    probability: int
    expected_close_date: date | None
    source: str | None
    channel: OpportunityChannel
    interested_products: list[str]
    next_action: str | None
    next_action_at: datetime | None
    lost_reason: str | None
    won_at: datetime | None
    created_at: datetime
    updated_at: datetime


class StageChangeRequest(BaseModel):
    stage: OpportunityStage
    lost_reason: str | None = None


class AssignmentRequest(BaseModel):
    owner_id: UUID


class ActivityCreate(BaseModel):
    account_id: UUID | None = None
    contact_id: UUID | None = None
    opportunity_id: UUID | None = None
    owner_id: UUID | None = None
    activity_type: ActivityType
    outcome: str | None = Field(default=None, max_length=200)
    started_at: datetime
    completed_at: datetime | None = None
    notes: str | None = None
    next_action: str | None = Field(default=None, max_length=500)
    next_action_at: datetime | None = None
    create_follow_up: bool = False


class ActivityUpdate(BaseModel):
    outcome: str | None = Field(default=None, max_length=200)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str | None = None
    next_action: str | None = Field(default=None, max_length=500)
    next_action_at: datetime | None = None
    create_follow_up: bool = False


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    account_id: UUID | None
    contact_id: UUID | None
    opportunity_id: UUID | None
    owner_id: UUID
    activity_type: ActivityType
    outcome: str | None
    started_at: datetime
    completed_at: datetime | None
    notes: str | None
    next_action: str | None
    next_action_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PipelineStageSummary(BaseModel):
    stage: OpportunityStage
    deals: int
    value_cents: int
    weighted_value_cents: int


class LeaderboardRow(BaseModel):
    owner_id: UUID
    owner_name: str
    contacts: int
    meetings: int
    demos: int
    proposals: int
    signed: int
    activated: int
    won: int
    revenue_cents: int
    pipeline_cents: int
    weighted_pipeline_cents: int


class MyDayResponse(BaseModel):
    follow_ups_today: list[ActivityResponse]
    overdue: list[ActivityResponse]
    meetings: list[ActivityResponse]
    recent_activity: list[ActivityResponse]
    new_leads: list[AccountResponse]


class CsvPreviewRow(BaseModel):
    row_number: int
    values: dict[str, object]
    normalized_domain: str | None
    valid: bool
    errors: list[str]
    duplicate_account_id: UUID | None = None


class CsvParseResult(BaseModel):
    rows: list[CsvPreviewRow]
    valid_rows: int
    invalid_rows: int
    file_errors: list[str]


class AccountCsvRequest(BaseModel):
    csv_content: str = Field(min_length=1, max_length=5_000_000)


class AccountCsvImportRequest(AccountCsvRequest):
    confirm: bool


class AccountCsvImportResponse(BaseModel):
    imported: int
    account_ids: list[UUID]


class CaseStudyMetricsUpdate(BaseModel):
    baseline: dict[str, Any] | None = None
    runs: int | None = Field(default=None, ge=0)
    leads: int | None = Field(default=None, ge=0)
    qualified: int | None = Field(default=None, ge=0)
    meetings: int | None = Field(default=None, ge=0)
    hours_saved: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    conversion: Decimal | None = Field(default=None, ge=0, le=100, max_digits=7, decimal_places=4)
    notes: str | None = None
    period_start: date | None = None
    period_end: date | None = None

    @model_validator(mode="after")
    def validate_period(self) -> CaseStudyMetricsUpdate:
        if (
            self.period_start is not None
            and self.period_end is not None
            and self.period_end < self.period_start
        ):
            raise ValueError("period_end cannot be before period_start")
        return self


class CaseStudyMetricsResponse(CaseStudyMetricsUpdate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    account_id: UUID
    created_at: datetime
    updated_at: datetime
