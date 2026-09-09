from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import AuditResult
from app.audit.service import record_audit_log
from app.core.errors import ApiError
from app.db.session import get_db
from app.partners.models import Partner, PartnerAgreement, PartnerClient
from app.partners.schemas import (
    AgreementCreate,
    AgreementRead,
    PartnerClientCreate,
    PartnerClientRead,
    PartnerCreate,
    PartnerMetrics,
    PartnerRead,
    PartnerUpdate,
)
from app.partners.service import (
    archive_partner,
    attribute_client,
    create_agreement,
    create_partner,
    get_partner,
    list_partners,
    partner_metrics,
    update_partner,
)
from app.staff.dependencies import CurrentStaff, get_current_staff, require_csrf
from app.staff.permissions import Permission

router = APIRouter(prefix="/api/partners", tags=["partners"])


def _owner_scope(current: CurrentStaff, *, write: bool = False) -> UUID | None:
    full_permission = Permission.PARTNER_WRITE if write else Permission.PARTNER_READ
    if full_permission in current.permissions:
        return None
    if not write and Permission.PARTNER_READ_ASSIGNED in current.permissions:
        return current.staff.id
    raise ApiError(
        status_code=403, code="PERMISSION_DENIED", message="Non hai i permessi necessari."
    )


def _ensure_access(current: CurrentStaff, partner: Partner, *, write: bool = False) -> None:
    owner_scope = _owner_scope(current, write=write)
    if owner_scope is not None and partner.owner_staff_id != owner_scope:
        raise ApiError(
            status_code=403, code="PERMISSION_DENIED", message="Non hai i permessi necessari."
        )


def _audit_context(request: Request) -> tuple[str, str | None, str | None]:
    return (
        request.state.request_id,
        request.client.host if request.client is not None else None,
        request.headers.get("user-agent", "")[:256] or None,
    )


@router.get("", response_model=list[PartnerRead])
def partners(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(get_current_staff)],
) -> list[Partner]:
    return list_partners(db, owner_staff_id=_owner_scope(current))


@router.get("/metrics", response_model=PartnerMetrics)
def metrics(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(get_current_staff)],
) -> dict[str, int]:
    return partner_metrics(db, owner_staff_id=_owner_scope(current))


@router.post("", response_model=PartnerRead, status_code=201)
def add_partner(
    payload: PartnerCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(get_current_staff)],
    csrf_current: Annotated[CurrentStaff, Depends(require_csrf)],
) -> Partner:
    del csrf_current
    _owner_scope(current, write=True)
    partner = create_partner(db, payload)
    request_id, ip_address, user_agent = _audit_context(request)
    record_audit_log(
        db,
        actor_staff_id=current.staff.id,
        action="partner.created",
        entity_type="partner",
        entity_id=partner.id,
        previous=None,
        new={
            "name": partner.name,
            "owner_staff_id": str(partner.owner_staff_id) if partner.owner_staff_id else None,
        },
        request_id=request_id,
        ip_address=ip_address,
        user_agent_summary=user_agent,
        result=AuditResult.SUCCESS,
    )
    db.commit()
    return partner


@router.get("/{partner_id}", response_model=PartnerRead)
def partner_detail(
    partner_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(get_current_staff)],
) -> Partner:
    partner = get_partner(db, partner_id)
    _ensure_access(current, partner)
    return partner


@router.patch("/{partner_id}", response_model=PartnerRead)
def edit_partner(
    partner_id: UUID,
    payload: PartnerUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(get_current_staff)],
    csrf_current: Annotated[CurrentStaff, Depends(require_csrf)],
) -> Partner:
    del csrf_current
    partner = get_partner(db, partner_id)
    _ensure_access(current, partner, write=True)
    previous = {
        "name": partner.name,
        "status": partner.status.value,
        "owner_staff_id": str(partner.owner_staff_id) if partner.owner_staff_id else None,
    }
    update_partner(db, partner, payload)
    request_id, ip_address, user_agent = _audit_context(request)
    record_audit_log(
        db,
        actor_staff_id=current.staff.id,
        action="partner.updated",
        entity_type="partner",
        entity_id=partner.id,
        previous=previous,
        new={
            "name": partner.name,
            "status": partner.status.value,
            "owner_staff_id": str(partner.owner_staff_id) if partner.owner_staff_id else None,
        },
        request_id=request_id,
        ip_address=ip_address,
        user_agent_summary=user_agent,
        result=AuditResult.SUCCESS,
    )
    db.commit()
    return partner


@router.post("/{partner_id}/archive", response_model=PartnerRead)
def archive(
    partner_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(get_current_staff)],
    csrf_current: Annotated[CurrentStaff, Depends(require_csrf)],
) -> Partner:
    del csrf_current
    partner = get_partner(db, partner_id)
    _ensure_access(current, partner, write=True)
    archive_partner(db, partner, actor_id=current.staff.id)
    request_id, ip_address, user_agent = _audit_context(request)
    record_audit_log(
        db,
        actor_staff_id=current.staff.id,
        action="partner.archived",
        entity_type="partner",
        entity_id=partner.id,
        previous={"archived_at": None},
        new={"archived_at": partner.archived_at.isoformat() if partner.archived_at else None},
        request_id=request_id,
        ip_address=ip_address,
        user_agent_summary=user_agent,
        result=AuditResult.SUCCESS,
    )
    db.commit()
    return partner


@router.get("/{partner_id}/agreements", response_model=list[AgreementRead])
def agreements(
    partner_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(get_current_staff)],
) -> list[PartnerAgreement]:
    partner = get_partner(db, partner_id)
    _ensure_access(current, partner)
    return list(
        db.scalars(
            select(PartnerAgreement)
            .where(
                PartnerAgreement.partner_id == partner.id,
                PartnerAgreement.archived_at.is_(None),
            )
            .order_by(PartnerAgreement.version.desc())
        )
    )


@router.post("/{partner_id}/agreements", response_model=AgreementRead, status_code=201)
def add_agreement(
    partner_id: UUID,
    payload: AgreementCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(get_current_staff)],
    csrf_current: Annotated[CurrentStaff, Depends(require_csrf)],
) -> PartnerAgreement:
    del csrf_current
    partner = get_partner(db, partner_id)
    _ensure_access(current, partner, write=True)
    agreement = create_agreement(db, partner=partner, payload=payload, actor_id=current.staff.id)
    request_id, ip_address, user_agent = _audit_context(request)
    record_audit_log(
        db,
        actor_staff_id=current.staff.id,
        action="partner.agreement.created",
        entity_type="partner_agreement",
        entity_id=agreement.id,
        previous=None,
        new={
            "partner_id": str(partner.id),
            "version": agreement.version,
            "partner_share_bps": agreement.partner_share_bps,
            "sift_share_bps": agreement.sift_share_bps,
        },
        request_id=request_id,
        ip_address=ip_address,
        user_agent_summary=user_agent,
        result=AuditResult.SUCCESS,
    )
    db.commit()
    return agreement


@router.get("/{partner_id}/clients", response_model=list[PartnerClientRead])
def clients(
    partner_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(get_current_staff)],
) -> list[PartnerClient]:
    partner = get_partner(db, partner_id)
    _ensure_access(current, partner)
    return list(
        db.scalars(
            select(PartnerClient)
            .where(
                PartnerClient.partner_id == partner.id,
                PartnerClient.archived_at.is_(None),
            )
            .order_by(PartnerClient.attributed_at.desc())
        )
    )


@router.post("/{partner_id}/clients", response_model=PartnerClientRead, status_code=201)
def add_client(
    partner_id: UUID,
    payload: PartnerClientCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(get_current_staff)],
    csrf_current: Annotated[CurrentStaff, Depends(require_csrf)],
) -> PartnerClient:
    del csrf_current
    partner = get_partner(db, partner_id)
    _ensure_access(current, partner, write=True)
    client = attribute_client(db, partner=partner, payload=payload)
    request_id, ip_address, user_agent = _audit_context(request)
    record_audit_log(
        db,
        actor_staff_id=current.staff.id,
        action="partner.client.attributed",
        entity_type="partner_client",
        entity_id=client.id,
        previous=None,
        new={
            "partner_id": str(partner.id),
            "external_client_id": str(client.external_client_id),
            "gross_revenue_cents": client.gross_revenue_cents,
            "partner_share_cents": client.partner_share_cents,
            "sift_share_cents": client.sift_share_cents,
        },
        request_id=request_id,
        ip_address=ip_address,
        user_agent_summary=user_agent,
        result=AuditResult.SUCCESS,
    )
    db.commit()
    return client
