from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"

    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff_members.id", ondelete="SET NULL")
    )


class ProductServiceCredential(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "product_service_credentials"
    __table_args__ = (Index("ix_product_credentials_active", "product_id", "revoked_at"),)

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("staff_members.id", ondelete="RESTRICT"), nullable=False
    )
    rotated_from_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_service_credentials.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff_members.id", ondelete="SET NULL")
    )


class ProductRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "product_runs"
    __table_args__ = (
        UniqueConstraint("product_id", "external_run_id", name="uq_product_external_run"),
        CheckConstraint("event_count >= 0", name="ck_product_run_event_count"),
        CheckConstraint("cost_cents >= 0", name="ck_product_run_cost_cents"),
        CheckConstraint("units >= 0", name="ck_product_run_units"),
        Index("ix_product_runs_status", "product_id", "status"),
        Index("ix_product_runs_started", "product_id", "started_at"),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    external_run_id: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="running", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    event_count: Mapped[int] = mapped_column(default=0, nullable=False)
    cost_cents: Mapped[int] = mapped_column(default=0, nullable=False)
    units: Mapped[int] = mapped_column(default=0, nullable=False)
    run_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)


class ProductEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "product_events"
    __table_args__ = (
        CheckConstraint("schema_version > 0", name="ck_product_event_schema_version"),
        CheckConstraint("cost_cents >= 0", name="ck_product_event_cost_cents"),
        CheckConstraint("units >= 0", name="ck_product_event_units"),
        Index("ix_product_events_product_occurred", "product_id", "occurred_at"),
        Index("ix_product_events_run", "product_run_id"),
        Index("ix_product_events_type", "event_type"),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    product_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_runs.id", ondelete="SET NULL")
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    schema_version: Mapped[int] = mapped_column(default=1, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    external_run_id: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str | None] = mapped_column(String(40))
    cost_cents: Mapped[int] = mapped_column(default=0, nullable=False)
    units: Mapped[int] = mapped_column(default=0, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)
