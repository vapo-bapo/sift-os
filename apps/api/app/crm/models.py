from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin, enum_type


class AccountType(StrEnum):
    PROSPECT_AGENCY = "prospect_agency"
    PARTNER_AGENCY = "partner_agency"
    DIRECT_PROSPECT = "direct_prospect"
    DIRECT_CUSTOMER = "direct_customer"
    CASE_STUDY = "case_study"
    CUSTOMER = "customer"
    OTHER = "other"


class AccountStatus(StrEnum):
    NEW = "new"
    ACTIVE = "active"
    INACTIVE = "inactive"


class PreferredChannel(StrEnum):
    EMAIL = "email"
    PHONE = "phone"
    LINKEDIN = "linkedin"
    WHATSAPP = "whatsapp"
    OTHER = "other"


class OpportunityStage(StrEnum):
    PROSPECT = "prospect"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    MEETING = "meeting"
    DEMO = "demo"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    PARTNER_SIGNED = "partner_signed"
    PARTNER_ACTIVATED = "partner_activated"
    WON = "won"
    LOST = "lost"
    DISQUALIFIED = "disqualified"


class OpportunityStatus(StrEnum):
    OPEN = "open"
    WON = "won"
    LOST = "lost"
    DISQUALIFIED = "disqualified"


class OpportunityChannel(StrEnum):
    AGENCY_PARTNER = "agency_partner"
    DIRECT_SALES = "direct_sales"
    REFERRAL = "referral"
    INBOUND = "inbound"
    OTHER = "other"


class ActivityType(StrEnum):
    CALL = "call"
    EMAIL = "email"
    LINKEDIN = "linkedin"
    WHATSAPP = "whatsapp"
    MEETING = "meeting"
    DEMO = "demo"
    PROPOSAL = "proposal"
    FOLLOW_UP = "follow_up"
    NOTE = "note"
    OTHER = "other"


class CrmAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crm_accounts"
    __table_args__ = (
        CheckConstraint("lead_score >= 0 AND lead_score <= 100", name="ck_crm_account_lead_score"),
        Index(
            "uq_crm_accounts_normalized_domain_active",
            "normalized_domain",
            unique=True,
            postgresql_where=text("archived_at IS NULL AND normalized_domain IS NOT NULL"),
        ),
        Index("ix_crm_accounts_owner_status", "owner_id", "status"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(253))
    normalized_domain: Mapped[str | None] = mapped_column(String(253))
    website: Mapped[str | None] = mapped_column(String(500))
    industry: Mapped[str | None] = mapped_column(String(100))
    company_size: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str | None] = mapped_column(String(2))
    city: Mapped[str | None] = mapped_column(String(100))
    account_type: Mapped[AccountType] = mapped_column(
        enum_type(AccountType, "crm_account_type"), default=AccountType.DIRECT_PROSPECT
    )
    source: Mapped[str | None] = mapped_column(String(100))
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("staff_members.id"), index=True)
    status: Mapped[AccountStatus] = mapped_column(
        enum_type(AccountStatus, "crm_account_status"), default=AccountStatus.NEW
    )
    lead_score: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class CrmContact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crm_contacts"
    __table_args__ = (
        UniqueConstraint("normalized_email", name="uq_crm_contacts_normalized_email"),
        UniqueConstraint("account_id", "normalized_phone", name="uq_crm_contacts_account_phone"),
        UniqueConstraint("account_id", "normalized_name", name="uq_crm_contacts_account_name"),
        Index("ix_crm_contacts_account", "account_id"),
    )

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_accounts.id", ondelete="CASCADE"), nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(201), nullable=False)
    role: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(320))
    normalized_email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(50))
    normalized_phone: Mapped[str | None] = mapped_column(String(50))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    preferred_channel: Mapped[PreferredChannel | None] = mapped_column(
        enum_type(PreferredChannel, "crm_preferred_channel")
    )
    is_decision_maker: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)


class CrmOpportunity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crm_opportunities"
    __table_args__ = (
        CheckConstraint("estimated_value_cents >= 0", name="ck_crm_opportunity_value"),
        CheckConstraint("probability >= 0 AND probability <= 100", name="ck_crm_probability"),
        CheckConstraint(
            "weighted_value_cents = (estimated_value_cents * probability) / 100",
            name="ck_crm_weighted_value",
        ),
        Index("ix_crm_opportunities_owner_stage", "owner_id", "stage"),
        Index("ix_crm_opportunities_next_action", "next_action_at"),
    )

    account_id: Mapped[UUID] = mapped_column(ForeignKey("crm_accounts.id"), index=True)
    primary_contact_id: Mapped[UUID | None] = mapped_column(ForeignKey("crm_contacts.id"))
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("staff_members.id"), index=True)
    stage: Mapped[OpportunityStage] = mapped_column(
        enum_type(OpportunityStage, "crm_opportunity_stage")
    )
    status: Mapped[OpportunityStatus] = mapped_column(
        enum_type(OpportunityStatus, "crm_opportunity_status"), default=OpportunityStatus.OPEN
    )
    estimated_value_cents: Mapped[int] = mapped_column(Integer, default=0)
    weighted_value_cents: Mapped[int] = mapped_column(Integer, default=0)
    probability: Mapped[int] = mapped_column(Integer, default=0)
    expected_close_date: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str | None] = mapped_column(String(100))
    channel: Mapped[OpportunityChannel] = mapped_column(
        enum_type(OpportunityChannel, "crm_opportunity_channel"),
        default=OpportunityChannel.DIRECT_SALES,
    )
    interested_products: Mapped[list[str]] = mapped_column(ARRAY(String(100)), default=list)
    next_action: Mapped[str | None] = mapped_column(String(500))
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lost_reason: Mapped[str | None] = mapped_column(Text)
    won_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OpportunityStageHistory(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "opportunity_stage_history"
    __table_args__ = (
        Index("ix_stage_history_opportunity_created", "opportunity_id", "created_at"),
    )

    opportunity_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_opportunities.id", ondelete="CASCADE"), nullable=False
    )
    previous_stage: Mapped[OpportunityStage | None] = mapped_column(
        enum_type(OpportunityStage, "crm_opportunity_stage")
    )
    new_stage: Mapped[OpportunityStage] = mapped_column(
        enum_type(OpportunityStage, "crm_opportunity_stage"), nullable=False
    )
    changed_by: Mapped[UUID] = mapped_column(ForeignKey("staff_members.id"), nullable=False)


class CrmActivity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crm_activities"
    __table_args__ = (
        CheckConstraint(
            "account_id IS NOT NULL OR contact_id IS NOT NULL OR opportunity_id IS NOT NULL",
            name="ck_crm_activity_subject",
        ),
        Index("ix_crm_activities_owner_started", "owner_id", "started_at"),
        Index("ix_crm_activities_owner_next", "owner_id", "next_action_at"),
    )

    account_id: Mapped[UUID | None] = mapped_column(ForeignKey("crm_accounts.id"), index=True)
    contact_id: Mapped[UUID | None] = mapped_column(ForeignKey("crm_contacts.id"))
    opportunity_id: Mapped[UUID | None] = mapped_column(ForeignKey("crm_opportunities.id"))
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("staff_members.id"), index=True)
    activity_type: Mapped[ActivityType] = mapped_column(
        enum_type(ActivityType, "crm_activity_type")
    )
    outcome: Mapped[str | None] = mapped_column(String(200))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    next_action: Mapped[str | None] = mapped_column(String(500))
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CrmCaseStudyMetrics(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crm_case_study_metrics"
    __table_args__ = (
        UniqueConstraint("account_id", name="uq_crm_case_study_metrics_account"),
        CheckConstraint("runs IS NULL OR runs >= 0", name="ck_case_study_runs"),
        CheckConstraint("leads IS NULL OR leads >= 0", name="ck_case_study_leads"),
        CheckConstraint("qualified IS NULL OR qualified >= 0", name="ck_case_study_qualified"),
        CheckConstraint("meetings IS NULL OR meetings >= 0", name="ck_case_study_meetings"),
        CheckConstraint("hours_saved IS NULL OR hours_saved >= 0", name="ck_case_study_hours"),
        CheckConstraint(
            "conversion IS NULL OR (conversion >= 0 AND conversion <= 100)",
            name="ck_case_study_conversion",
        ),
        CheckConstraint(
            "period_end IS NULL OR period_start IS NULL OR period_end >= period_start",
            name="ck_case_study_period",
        ),
    )

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_accounts.id", ondelete="CASCADE"), nullable=False
    )
    baseline: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    runs: Mapped[int | None] = mapped_column(Integer)
    leads: Mapped[int | None] = mapped_column(Integer)
    qualified: Mapped[int | None] = mapped_column(Integer)
    meetings: Mapped[int | None] = mapped_column(Integer)
    hours_saved: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    conversion: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    notes: Mapped[str | None] = mapped_column(Text)
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
