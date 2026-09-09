from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import AuditResult
from app.audit.service import record_audit_log
from app.core.errors import ApiError
from app.crm.models import CrmOpportunity, OpportunityStatus
from app.db.session import get_db
from app.finance.models import FinancialEntry, FinancialEntryType, FinancialSnapshot
from app.finance.schemas import (
    FinanceMetrics,
    FinancialEntryCreate,
    FinancialEntryList,
    FinancialEntryPatch,
    FinancialEntryResponse,
    FinancialSnapshotCreate,
    FinancialSnapshotResponse,
)
from app.finance.service import (
    calculate_finance_metrics,
    create_entry,
    create_snapshot,
    list_entries,
    update_entry,
)
from app.partners.models import PartnerClient
from app.staff.dependencies import CurrentStaff, require_csrf, require_permission
from app.staff.permissions import Permission

router = APIRouter(prefix="/api/finance", tags=["finance"])


@router.get("/entries", response_model=FinancialEntryList)
def entries(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(require_permission(Permission.FINANCE_READ))],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> FinancialEntryList:
    del current
    items, total = list_entries(db, page=page, page_size=page_size)
    return FinancialEntryList(items=items, total=total, page=page, page_size=page_size)


def _audit(
    request: Request,
    db: Session,
    current: CurrentStaff,
    action: str,
    item: FinancialEntry | FinancialSnapshot,
    previous: dict[str, object] | None,
) -> None:
    record_audit_log(
        db,
        actor_staff_id=current.staff.id,
        action=action,
        entity_type=item.__tablename__,
        entity_id=item.id,
        previous=previous,
        new={
            "id": str(item.id),
            "amount_cents": getattr(item, "amount_cents", getattr(item, "cash_cents", None)),
        },
        request_id=request.state.request_id,
        ip_address=request.client.host if request.client else None,
        user_agent_summary=request.headers.get("user-agent", "")[:256] or None,
        result=AuditResult.SUCCESS,
    )


@router.post("/entries", response_model=FinancialEntryResponse, status_code=201)
def entry_create(
    payload: FinancialEntryCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(require_csrf)],
) -> FinancialEntryResponse:
    if Permission.FINANCE_WRITE not in current.permissions:
        raise ApiError(
            status_code=403, code="PERMISSION_DENIED", message="Non hai i permessi necessari."
        )
    item = create_entry(db, payload, current.staff.id)
    _audit(request, db, current, "finance.entry.create", item, None)
    db.commit()
    db.refresh(item)
    return FinancialEntryResponse.model_validate(item)


@router.patch("/entries/{entry_id}", response_model=FinancialEntryResponse)
def entry_update(
    entry_id: UUID,
    payload: FinancialEntryPatch,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(require_csrf)],
) -> FinancialEntryResponse:
    if Permission.FINANCE_WRITE not in current.permissions:
        raise ApiError(
            status_code=403, code="PERMISSION_DENIED", message="Non hai i permessi necessari."
        )
    existing = db.get(FinancialEntry, entry_id)
    previous: dict[str, object] | None = (
        {"amount_cents": existing.amount_cents, "entry_type": existing.entry_type.value}
        if existing
        else None
    )
    item = update_entry(db, entry_id, payload, current.staff.id)
    if item is None:
        raise ApiError(
            status_code=404, code="FINANCE_ENTRY_NOT_FOUND", message="Movimento non trovato."
        )
    _audit(request, db, current, "finance.entry.update", item, previous)
    db.commit()
    db.refresh(item)
    return FinancialEntryResponse.model_validate(item)


@router.get("/snapshots", response_model=list[FinancialSnapshotResponse])
def snapshots(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(require_permission(Permission.FINANCE_READ))],
) -> list[FinancialSnapshotResponse]:
    del current
    return [
        FinancialSnapshotResponse.model_validate(item)
        for item in db.scalars(
            select(FinancialSnapshot).order_by(FinancialSnapshot.date.desc()).limit(100)
        )
    ]


@router.post("/snapshots", response_model=FinancialSnapshotResponse, status_code=201)
def snapshot_create(
    payload: FinancialSnapshotCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(require_csrf)],
) -> FinancialSnapshotResponse:
    if Permission.FINANCE_WRITE not in current.permissions:
        raise ApiError(
            status_code=403, code="PERMISSION_DENIED", message="Non hai i permessi necessari."
        )
    item = create_snapshot(db, payload, current.staff.id)
    _audit(request, db, current, "finance.snapshot.create", item, None)
    db.commit()
    db.refresh(item)
    return FinancialSnapshotResponse.model_validate(item)


@router.get("/metrics", response_model=FinanceMetrics)
def metrics(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(require_permission(Permission.FINANCE_READ))],
) -> FinanceMetrics:
    del current
    now = datetime.now(UTC)
    all_entries = list(
        db.scalars(select(FinancialEntry).where(FinancialEntry.archived_at.is_(None)))
    )
    snapshot = db.scalar(select(FinancialSnapshot).order_by(FinancialSnapshot.date.desc()).limit(1))
    opportunities = list(db.scalars(select(CrmOpportunity)))
    clients = list(db.scalars(select(PartnerClient).where(PartnerClient.archived_at.is_(None))))
    return calculate_finance_metrics(
        all_entries,
        as_of=now,
        cash_cents=snapshot.cash_cents if snapshot else 0,
        contracted_revenue_cents=sum(
            item.estimated_value_cents
            for item in opportunities
            if item.status is OpportunityStatus.WON
        ),
        pipeline_revenue_cents=sum(
            item.estimated_value_cents
            for item in opportunities
            if item.status is OpportunityStatus.OPEN
        ),
        weighted_pipeline_cents=sum(
            item.weighted_value_cents
            for item in opportunities
            if item.status is OpportunityStatus.OPEN
        ),
        commission_accrued_cents=sum(item.partner_share_cents for item in clients),
        commission_paid_cents=sum(
            item.amount_cents
            for item in all_entries
            if item.entry_type is FinancialEntryType.PARTNER_COMMISSION
        ),
    )
