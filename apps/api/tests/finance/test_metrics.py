from datetime import UTC, date, datetime

from app.finance.models import FinancialEntry, FinancialEntryType
from app.finance.service import calculate_finance_metrics


def entry(
    entry_type: FinancialEntryType, amount_cents: int, *, recurring: bool = False
) -> FinancialEntry:
    return FinancialEntry(
        date=date(2026, 9, 9),
        entry_type=entry_type,
        category="test",
        amount_cents=amount_cents,
        currency="EUR",
        recurring=recurring,
        created_by_id=None,
    )


def test_finance_metrics_keep_money_in_integer_cents() -> None:
    metrics = calculate_finance_metrics(
        [
            entry(FinancialEntryType.REVENUE, 125_000, recurring=True),
            entry(FinancialEntryType.CLOUD_COST, 25_000, recurring=True),
            entry(FinancialEntryType.API_COST, 10_000),
        ],
        as_of=datetime(2026, 9, 9, 12, 0, tzinfo=UTC),
        cash_cents=500_000,
        contracted_revenue_cents=200_000,
        pipeline_revenue_cents=300_000,
        weighted_pipeline_cents=150_000,
        commission_accrued_cents=20_000,
        commission_paid_cents=5_000,
    )

    assert metrics.cash_cents == 500_000
    assert metrics.revenue_mtd_cents == 125_000
    assert metrics.cost_mtd_cents == 35_000
    assert metrics.mrr_cents == 125_000
    assert metrics.arr_cents == 1_500_000
    assert metrics.gross_margin_cents == 90_000
    assert metrics.partner_commission_payable_cents == 15_000
    assert all(isinstance(value, int) for value in metrics.model_dump().values())
