from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.errors import ApiError
from app.partners.models import Partner, PartnerAgreement, PartnerClient, PartnerStatus
from app.partners.schemas import AgreementCreate, PartnerClientCreate, PartnerCreate, PartnerUpdate


@dataclass(frozen=True, slots=True)
class RevenueSplit:
    partner_share_cents: int
    sift_share_cents: int


def calculate_revenue_share(
    *, gross_revenue_cents: int, partner_share_bps: int, sift_share_bps: int
) -> RevenueSplit:
    if gross_revenue_cents < 0:
        raise ValueError("gross revenue must be non-negative")
    if partner_share_bps < 0 or sift_share_bps < 0 or partner_share_bps + sift_share_bps != 10_000:
        raise ValueError("revenue shares must total 10,000 basis points")
    partner_cents = gross_revenue_cents * partner_share_bps // 10_000
    return RevenueSplit(
        partner_share_cents=partner_cents,
        sift_share_cents=gross_revenue_cents - partner_cents,
    )


def list_partners(db: Session, *, owner_staff_id: UUID | None = None) -> list[Partner]:
    query = select(Partner).where(Partner.archived_at.is_(None))
    if owner_staff_id is not None:
        query = query.where(Partner.owner_staff_id == owner_staff_id)
    return list(db.scalars(query.order_by(Partner.name, Partner.id)))


def get_partner(db: Session, partner_id: UUID, *, include_archived: bool = False) -> Partner:
    query = select(Partner).where(Partner.id == partner_id)
    if not include_archived:
        query = query.where(Partner.archived_at.is_(None))
    partner = db.scalar(query)
    if partner is None:
        raise ApiError(status_code=404, code="PARTNER_NOT_FOUND", message="Partner non trovato.")
    return partner


def create_partner(db: Session, payload: PartnerCreate) -> Partner:
    partner = Partner(**payload.model_dump(), status=PartnerStatus.PROSPECT)
    db.add(partner)
    db.flush()
    return partner


def update_partner(db: Session, partner: Partner, payload: PartnerUpdate) -> Partner:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(partner, field, value)
    now = datetime.now(UTC)
    if partner.status == PartnerStatus.SIGNED and partner.signed_at is None:
        partner.signed_at = now
    if partner.status == PartnerStatus.ACTIVE and partner.activated_at is None:
        partner.activated_at = now
    db.flush()
    return partner


def archive_partner(db: Session, partner: Partner, *, actor_id: UUID) -> Partner:
    partner.archived_at = datetime.now(UTC)
    partner.archived_by = actor_id
    db.flush()
    return partner


def create_agreement(
    db: Session, *, partner: Partner, payload: AgreementCreate, actor_id: UUID
) -> PartnerAgreement:
    previous = list(
        db.scalars(
            select(PartnerAgreement)
            .where(
                PartnerAgreement.partner_id == partner.id,
                PartnerAgreement.archived_at.is_(None),
            )
            .order_by(PartnerAgreement.version.desc())
            .with_for_update()
        )
    )
    version = previous[0].version + 1 if previous else 1
    agreement = PartnerAgreement(
        partner_id=partner.id,
        version=version,
        created_by=actor_id,
        **payload.model_dump(),
    )
    db.add(agreement)
    db.flush()
    return agreement


def _effective_agreement(
    db: Session, *, partner_id: UUID, at: datetime, currency: str
) -> PartnerAgreement:
    agreement = db.scalar(
        select(PartnerAgreement)
        .where(
            PartnerAgreement.partner_id == partner_id,
            PartnerAgreement.archived_at.is_(None),
            PartnerAgreement.currency == currency.upper(),
            PartnerAgreement.effective_from <= at,
            or_(PartnerAgreement.effective_to.is_(None), PartnerAgreement.effective_to > at),
        )
        .order_by(PartnerAgreement.effective_from.desc(), PartnerAgreement.version.desc())
    )
    if agreement is None:
        raise ApiError(
            status_code=409,
            code="PARTNER_AGREEMENT_MISSING",
            message="Nessun accordo attivo per data e valuta indicate.",
        )
    return agreement


def attribute_client(
    db: Session, *, partner: Partner, payload: PartnerClientCreate
) -> PartnerClient:
    attributed_at = payload.attributed_at or datetime.now(UTC)
    currency = payload.currency.upper()
    agreement = _effective_agreement(db, partner_id=partner.id, at=attributed_at, currency=currency)
    split = calculate_revenue_share(
        gross_revenue_cents=payload.gross_revenue_cents,
        partner_share_bps=agreement.partner_share_bps,
        sift_share_bps=agreement.sift_share_bps,
    )
    client = PartnerClient(
        partner_id=partner.id,
        agreement_id=agreement.id,
        external_client_id=payload.external_client_id,
        client_name=payload.client_name,
        attributed_at=attributed_at,
        gross_revenue_cents=payload.gross_revenue_cents,
        partner_share_cents=split.partner_share_cents,
        sift_share_cents=split.sift_share_cents,
        currency=currency,
    )
    db.add(client)
    if partner.first_customer_at is None:
        partner.first_customer_at = attributed_at
    if partner.status in {
        PartnerStatus.PROSPECT,
        PartnerStatus.NEGOTIATING,
        PartnerStatus.SIGNED,
        PartnerStatus.ONBOARDING,
    }:
        partner.status = PartnerStatus.ACTIVE
        partner.activated_at = attributed_at
    db.flush()
    return client


def partner_metrics(db: Session, *, owner_staff_id: UUID | None = None) -> dict[str, int]:
    partner_filter: list[ColumnElement[bool]] = [Partner.archived_at.is_(None)]
    if owner_staff_id is not None:
        partner_filter.append(Partner.owner_staff_id == owner_staff_id)
    partners_total = db.scalar(select(func.count(Partner.id)).where(*partner_filter)) or 0
    partners_active = (
        db.scalar(
            select(func.count(Partner.id)).where(
                *partner_filter, Partner.status == PartnerStatus.ACTIVE
            )
        )
        or 0
    )
    client_row = db.execute(
        select(
            func.count(PartnerClient.id),
            func.coalesce(func.sum(PartnerClient.gross_revenue_cents), 0),
            func.coalesce(func.sum(PartnerClient.partner_share_cents), 0),
            func.coalesce(func.sum(PartnerClient.sift_share_cents), 0),
        )
        .join(Partner, Partner.id == PartnerClient.partner_id)
        .where(*partner_filter, PartnerClient.archived_at.is_(None))
    ).one()
    return {
        "partners_total": partners_total,
        "partners_active": partners_active,
        "attributed_clients": client_row[0],
        "gross_revenue_cents": client_row[1],
        "partner_share_cents": client_row[2],
        "sift_share_cents": client_row[3],
    }
