from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.finance.models import FinancialEntry, FinancialEntryType, FinancialSnapshot
from app.finance.schemas import (
    FinanceMetrics,
    FinancialEntryCreate,
    FinancialEntryPatch,
    FinancialSnapshotCreate,
)


def calculate_finance_metrics(
    entries: list[FinancialEntry],
    *,
    as_of: datetime,
    cash_cents: int = 0,
    contracted_revenue_cents: int = 0,
    pipeline_revenue_cents: int = 0,
    weighted_pipeline_cents: int = 0,
    commission_accrued_cents: int = 0,
    commission_paid_cents: int = 0,
) -> FinanceMetrics:
    month_entries = [
        item
        for item in entries
        if item.archived_at is None
        and item.date.year == as_of.year
        and item.date.month == as_of.month
    ]
    revenue = sum(
        item.amount_cents for item in month_entries if item.entry_type is FinancialEntryType.REVENUE
    )
    costs = sum(
        item.amount_cents
        for item in month_entries
        if item.entry_type is not FinancialEntryType.REVENUE
    )
    recurring_revenue = sum(
        item.amount_cents
        for item in entries
        if item.archived_at is None
        and item.recurring
        and item.entry_type is FinancialEntryType.REVENUE
    )
    api_cloud = sum(
        item.amount_cents
        for item in month_entries
        if item.entry_type in {FinancialEntryType.API_COST, FinancialEntryType.CLOUD_COST}
    )
    payable = max(commission_accrued_cents - commission_paid_cents, 0)
    return FinanceMetrics(
        cash_cents=int(cash_cents),
        burn_cents=int(max(costs - revenue, 0)),
        mrr_cents=int(recurring_revenue),
        arr_cents=int(recurring_revenue * 12),
        contracted_revenue_cents=int(contracted_revenue_cents),
        pipeline_revenue_cents=int(pipeline_revenue_cents),
        weighted_pipeline_cents=int(weighted_pipeline_cents),
        revenue_mtd_cents=int(revenue),
        cost_mtd_cents=int(costs),
        api_cloud_cost_cents=int(api_cloud),
        gross_margin_cents=int(revenue - costs),
        partner_commission_accrued_cents=int(commission_accrued_cents),
        partner_commission_paid_cents=int(commission_paid_cents),
        partner_commission_payable_cents=int(payable),
    )


def list_entries(db: Session, *, page: int, page_size: int) -> tuple[list[FinancialEntry], int]:
    criteria = FinancialEntry.archived_at.is_(None)
    total = db.scalar(select(func.count()).select_from(FinancialEntry).where(criteria)) or 0
    items = list(
        db.scalars(
            select(FinancialEntry)
            .where(criteria)
            .order_by(FinancialEntry.date.desc(), FinancialEntry.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, total


def create_entry(db: Session, payload: FinancialEntryCreate, created_by_id: UUID) -> FinancialEntry:
    item = FinancialEntry(**payload.model_dump(), created_by_id=created_by_id)
    db.add(item)
    db.flush()
    return item


def update_entry(
    db: Session, entry_id: UUID, payload: FinancialEntryPatch, actor_id: UUID
) -> FinancialEntry | None:
    item = db.get(FinancialEntry, entry_id)
    if item is None or item.archived_at is not None:
        return None
    for key, value in payload.model_dump(exclude_unset=True, exclude={"archive"}).items():
        setattr(item, key, value)
    if payload.archive:
        item.archived_at = datetime.now(UTC)
        item.archived_by_id = actor_id
    db.flush()
    return item


def create_snapshot(
    db: Session, payload: FinancialSnapshotCreate, created_by_id: UUID
) -> FinancialSnapshot:
    snapshot = FinancialSnapshot(**payload.model_dump(), created_by_id=created_by_id)
    db.add(snapshot)
    db.flush()
    return snapshot
