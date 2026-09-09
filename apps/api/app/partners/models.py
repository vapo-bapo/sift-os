from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_type


class PartnerStatus(StrEnum):
    PROSPECT = "prospect"
    NEGOTIATING = "negotiating"
    SIGNED = "signed"
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"


class Partner(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "partners"
    __table_args__ = (
        Index("ix_partners_owner_status", "owner_staff_id", "status"),
        Index("ix_partners_name", "name"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(240))
    email: Mapped[str | None] = mapped_column(String(320), index=True)
    domain: Mapped[str | None] = mapped_column(String(253), index=True)
    owner_staff_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff_members.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[PartnerStatus] = mapped_column(
        enum_type(PartnerStatus, "partner_status"), default=PartnerStatus.PROSPECT, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(String(4000))
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_customer_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    archived_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff_members.id", ondelete="SET NULL")
    )


class PartnerAgreement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "partner_agreements"
    __table_args__ = (
        UniqueConstraint("partner_id", "version", name="uq_partner_agreement_version"),
        CheckConstraint(
            "partner_share_bps >= 0 AND partner_share_bps <= 10000",
            name="ck_partner_agreement_partner_bps",
        ),
        CheckConstraint(
            "sift_share_bps >= 0 AND sift_share_bps <= 10000",
            name="ck_partner_agreement_sift_bps",
        ),
        CheckConstraint(
            "partner_share_bps + sift_share_bps = 10000",
            name="ck_partner_agreement_total_bps",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_partner_agreement_dates",
        ),
        Index("ix_partner_agreements_effective", "partner_id", "effective_from"),
    )

    partner_id: Mapped[UUID] = mapped_column(
        ForeignKey("partners.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    partner_share_bps: Mapped[int] = mapped_column(nullable=False)
    sift_share_bps: Mapped[int] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    terms: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("staff_members.id", ondelete="RESTRICT"), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff_members.id", ondelete="SET NULL")
    )


class PartnerClient(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "partner_clients"
    __table_args__ = (
        UniqueConstraint("partner_id", "external_client_id", name="uq_partner_external_client"),
        CheckConstraint("gross_revenue_cents >= 0", name="ck_partner_client_gross_cents"),
        CheckConstraint("partner_share_cents >= 0", name="ck_partner_client_partner_cents"),
        CheckConstraint("sift_share_cents >= 0", name="ck_partner_client_sift_cents"),
        CheckConstraint(
            "partner_share_cents + sift_share_cents = gross_revenue_cents",
            name="ck_partner_client_split_cents",
        ),
        Index("ix_partner_clients_attributed", "partner_id", "attributed_at"),
    )

    partner_id: Mapped[UUID] = mapped_column(
        ForeignKey("partners.id", ondelete="CASCADE"), nullable=False
    )
    agreement_id: Mapped[UUID] = mapped_column(
        ForeignKey("partner_agreements.id", ondelete="RESTRICT"), nullable=False
    )
    external_client_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    client_name: Mapped[str] = mapped_column(String(240), nullable=False)
    attributed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    gross_revenue_cents: Mapped[int] = mapped_column(nullable=False)
    partner_share_cents: Mapped[int] = mapped_column(nullable=False)
    sift_share_cents: Mapped[int] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff_members.id", ondelete="SET NULL")
    )
