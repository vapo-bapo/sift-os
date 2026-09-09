from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_type


class FinancialEntryType(StrEnum):
    REVENUE = "revenue"
    RECURRING_COST = "recurring_cost"
    ONE_TIME_COST = "one_time_cost"
    API_COST = "api_cost"
    CLOUD_COST = "cloud_cost"
    PROFESSIONAL_SERVICE = "professional_service"
    PARTNER_COMMISSION = "partner_commission"
    OTHER = "other"


class FinancialEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "financial_entries"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="ck_financial_entry_amount_positive"),
    )

    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    entry_type: Mapped[FinancialEntryType] = mapped_column(
        enum_type(FinancialEntryType, "financial_entry_type"), index=True
    )
    category: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("crm_accounts.id", ondelete="SET NULL"), index=True
    )
    partner_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("partners.id", ondelete="SET NULL"), index=True
    )
    product_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), index=True
    )
    recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str | None] = mapped_column(String(160))
    note: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff_members.id", ondelete="SET NULL"), index=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    archived_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff_members.id", ondelete="SET NULL")
    )


class FinancialSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "financial_snapshots"

    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    cash_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff_members.id", ondelete="SET NULL")
    )
