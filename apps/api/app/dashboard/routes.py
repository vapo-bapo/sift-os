from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select, true
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.company.models import Objective, Task, TaskStatus
from app.crm.models import (
    ActivityType,
    CrmActivity,
    CrmOpportunity,
    OpportunityStage,
    OpportunityStageHistory,
    OpportunityStatus,
)
from app.db.session import get_db
from app.finance.models import FinancialEntry, FinancialEntryType, FinancialSnapshot
from app.finance.service import calculate_finance_metrics
from app.partners.models import Partner, PartnerClient, PartnerStatus
from app.products.models import Product, ProductRun
from app.staff.dependencies import CurrentStaff, get_current_staff
from app.staff.permissions import Permission

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _day_bounds() -> tuple[datetime, datetime]:
    local_now = datetime.now(ZoneInfo("Europe/Rome"))
    start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.astimezone(UTC), (start + timedelta(days=1)).astimezone(UTC)


def _window() -> tuple[datetime, datetime]:
    return _day_bounds()


def _sales_scope(current: CurrentStaff) -> ColumnElement[bool]:
    if Permission.SALES_READ_ALL in current.permissions:
        return true()
    return CrmOpportunity.owner_id == current.staff.id


def sales_metrics(db: Session, current: CurrentStaff) -> dict[str, Any]:
    scope = _sales_scope(current)
    open_filter = [scope, CrmOpportunity.status == OpportunityStatus.OPEN]
    pipeline, weighted = db.execute(
        select(
            func.coalesce(func.sum(CrmOpportunity.estimated_value_cents), 0),
            func.coalesce(func.sum(CrmOpportunity.weighted_value_cents), 0),
        ).where(*open_filter)
    ).one()
    won = (
        db.scalar(
            select(func.count())
            .select_from(CrmOpportunity)
            .where(scope, CrmOpportunity.status == OpportunityStatus.WON)
        )
        or 0
    )
    lost = (
        db.scalar(
            select(func.count())
            .select_from(CrmOpportunity)
            .where(scope, CrmOpportunity.status == OpportunityStatus.LOST)
        )
        or 0
    )
    stages = {stage.value: 0 for stage in OpportunityStage}
    for stage, count in db.execute(
        select(CrmOpportunity.stage, func.count()).where(scope).group_by(CrmOpportunity.stage)
    ):
        stages[stage.value] = count
    partners_signed = (
        db.scalar(
            select(func.count())
            .select_from(Partner)
            .where(Partner.archived_at.is_(None), Partner.status != PartnerStatus.PROSPECT)
        )
        or 0
    )
    partners_active = (
        db.scalar(
            select(func.count())
            .select_from(Partner)
            .where(Partner.archived_at.is_(None), Partner.status == PartnerStatus.ACTIVE)
        )
        or 0
    )
    return {
        "pipeline_total_cents": int(pipeline),
        "pipeline_weighted_cents": int(weighted),
        "deals_won": won,
        "deals_lost": lost,
        "conversion_rate": round((won / (won + lost) * 100), 2) if won + lost else 0,
        "partners_signed": partners_signed,
        "partners_active": partners_active,
        "funnel": stages,
    }


def today_metrics(db: Session, current: CurrentStaff) -> dict[str, int]:
    start, end = _window()
    activity_scope = (
        true()
        if Permission.SALES_READ_ALL in current.permissions
        else CrmActivity.owner_id == current.staff.id
    )
    counts = {
        key: 0
        for key in (
            "outreach",
            "calls",
            "meetings",
            "demos",
            "proposals",
            "contracts",
            "partner_signed",
            "partner_activated",
        )
    }
    for activity_type, count in db.execute(
        select(CrmActivity.activity_type, func.count())
        .where(activity_scope, CrmActivity.started_at >= start, CrmActivity.started_at < end)
        .group_by(CrmActivity.activity_type)
    ):
        if activity_type in {
            ActivityType.CALL,
            ActivityType.EMAIL,
            ActivityType.LINKEDIN,
            ActivityType.WHATSAPP,
        }:
            counts["outreach"] += count
        if activity_type is ActivityType.CALL:
            counts["calls"] += count
        if activity_type is ActivityType.MEETING:
            counts["meetings"] += count
        if activity_type is ActivityType.DEMO:
            counts["demos"] += count
        if activity_type is ActivityType.PROPOSAL:
            counts["proposals"] += count
    for stage, count in db.execute(
        select(OpportunityStageHistory.new_stage, func.count())
        .where(
            OpportunityStageHistory.created_at >= start, OpportunityStageHistory.created_at < end
        )
        .group_by(OpportunityStageHistory.new_stage)
    ):
        if stage is OpportunityStage.WON:
            counts["contracts"] = count
        elif stage is OpportunityStage.PARTNER_SIGNED:
            counts["partner_signed"] = count
        elif stage is OpportunityStage.PARTNER_ACTIVATED:
            counts["partner_activated"] = count
    return counts


def product_metrics(db: Session) -> list[dict[str, Any]]:
    start, end = _window()
    results: list[dict[str, Any]] = []
    for product in db.scalars(
        select(Product).where(Product.active.is_(True)).order_by(Product.name)
    ):
        total, successes, failures, cost = db.execute(
            select(
                func.count(ProductRun.id),
                func.sum(case((ProductRun.status == "completed", 1), else_=0)),
                func.sum(case((ProductRun.status == "failed", 1), else_=0)),
                func.coalesce(func.sum(ProductRun.cost_cents), 0),
            ).where(
                ProductRun.product_id == product.id,
                ProductRun.started_at >= start,
                ProductRun.started_at < end,
            )
        ).one()
        successes = int(successes or 0)
        failures = int(failures or 0)
        total = int(total or 0)
        results.append(
            {
                "id": str(product.id),
                "code": product.code,
                "name": product.name,
                "status": "healthy" if failures == 0 else "degraded",
                "runs_today": total,
                "successful": successes,
                "failed": failures,
                "success_rate": round(successes / total * 100, 2) if total else 0,
                "cost_cents": int(cost),
            }
        )
    return results


def task_metrics(db: Session, current: CurrentStaff) -> dict[str, int]:
    scope = (
        true()
        if Permission.TASK_WRITE in current.permissions
        else Task.owner_id == current.staff.id
    )
    open_statuses = [
        TaskStatus.BACKLOG,
        TaskStatus.TODO,
        TaskStatus.IN_PROGRESS,
        TaskStatus.BLOCKED,
        TaskStatus.REVIEW,
    ]
    open_count = (
        db.scalar(
            select(func.count())
            .select_from(Task)
            .where(scope, Task.archived_at.is_(None), Task.status.in_(open_statuses))
        )
        or 0
    )
    overdue = (
        db.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                scope,
                Task.archived_at.is_(None),
                Task.status.in_(open_statuses),
                Task.due_date < datetime.now(ZoneInfo("Europe/Rome")).date(),
            )
        )
        or 0
    )
    objectives = (
        db.scalar(
            select(func.count()).select_from(Objective).where(Objective.archived_at.is_(None))
        )
        or 0
    )
    return {"open": open_count, "overdue": overdue, "objectives": objectives}


def finance_metrics(db: Session) -> dict[str, int]:
    entries = list(db.scalars(select(FinancialEntry).where(FinancialEntry.archived_at.is_(None))))
    snapshot = db.scalar(select(FinancialSnapshot).order_by(FinancialSnapshot.date.desc()).limit(1))
    opportunities = list(db.scalars(select(CrmOpportunity)))
    clients = list(db.scalars(select(PartnerClient).where(PartnerClient.archived_at.is_(None))))
    metrics = calculate_finance_metrics(
        entries,
        as_of=datetime.now(UTC),
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
            for item in entries
            if item.entry_type is FinancialEntryType.PARTNER_COMMISSION
        ),
    )
    return metrics.model_dump()


@router.get("")
def dashboard(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(get_current_staff)],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "tasks": task_metrics(db, current),
    }
    if Permission.DASHBOARD_SALES in current.permissions:
        payload["today"] = today_metrics(db, current)
        payload["sales"] = sales_metrics(db, current)
    if Permission.PRODUCT_READ in current.permissions:
        payload["products"] = product_metrics(db)
    if Permission.FINANCE_READ in current.permissions:
        payload["finance"] = finance_metrics(db)
    return payload


@router.get("/sales")
def dashboard_sales(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(get_current_staff)],
) -> dict[str, Any]:
    if Permission.DASHBOARD_SALES not in current.permissions:
        from app.core.errors import ApiError

        raise ApiError(
            status_code=403, code="PERMISSION_DENIED", message="Non hai i permessi necessari."
        )
    return {"today": today_metrics(db, current), **sales_metrics(db, current)}


@router.get("/products")
def dashboard_products(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(get_current_staff)],
) -> list[dict[str, Any]]:
    if Permission.PRODUCT_READ not in current.permissions:
        from app.core.errors import ApiError

        raise ApiError(
            status_code=403, code="PERMISSION_DENIED", message="Non hai i permessi necessari."
        )
    return product_metrics(db)


@router.get("/finance")
def dashboard_finance(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(get_current_staff)],
) -> dict[str, int]:
    if Permission.FINANCE_READ not in current.permissions:
        from app.core.errors import ApiError

        raise ApiError(
            status_code=403, code="PERMISSION_DENIED", message="Non hai i permessi necessari."
        )
    return finance_metrics(db)
