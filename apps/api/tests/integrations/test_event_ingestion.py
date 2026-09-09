from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.schemas import ProductEventIn
from app.integrations.service import ingest_product_event
from app.products.models import Product, ProductEvent, ProductRun
from app.products.service import product_metrics


@pytest.mark.integration
def test_event_id_is_idempotent_and_run_aggregation_is_transactional(
    db_session: Session,
) -> None:
    product = db_session.scalar(select(Product).where(Product.code == "ARGUS"))
    assert product is not None
    event_id = uuid4()
    started = ProductEventIn(
        event_id=event_id,
        event_type="run.started",
        occurred_at=datetime(2026, 9, 9, 8, 0, tzinfo=UTC),
        external_run_id="argus-run-1",
        cost_cents=10,
        units=2,
    )

    first = ingest_product_event(db_session, product_id=product.id, payload=started)
    duplicate = ingest_product_event(db_session, product_id=product.id, payload=started)
    completed = ingest_product_event(
        db_session,
        product_id=product.id,
        payload=ProductEventIn(
            event_id=uuid4(),
            event_type="run.completed",
            occurred_at=datetime(2026, 9, 9, 8, 5, tzinfo=UTC),
            external_run_id="argus-run-1",
            cost_cents=7,
            units=3,
        ),
    )

    run = db_session.scalar(select(ProductRun).where(ProductRun.id == first.run_id))
    assert first.duplicate is False
    assert duplicate.duplicate is True
    assert completed.duplicate is False
    assert run is not None
    assert run.event_count == 2
    assert run.cost_cents == 17
    assert run.units == 5
    assert run.status == "succeeded"
    assert run.completed_at == datetime(2026, 9, 9, 8, 5, tzinfo=UTC)
    assert len(list(db_session.scalars(select(ProductEvent)))) == 2


@pytest.mark.integration
def test_product_metrics_do_not_multiply_event_costs_by_number_of_runs(
    db_session: Session,
) -> None:
    product = db_session.scalar(select(Product).where(Product.code == "LYNX"))
    assert product is not None
    for run_number, cost in ((1, 11), (2, 13)):
        ingest_product_event(
            db_session,
            product_id=product.id,
            payload=ProductEventIn(
                event_id=uuid4(),
                event_type="run.completed",
                occurred_at=datetime(2026, 9, 9, 9, run_number, tzinfo=UTC),
                external_run_id=f"lynx-run-{run_number}",
                cost_cents=cost,
                units=1,
            ),
        )

    lynx = next(metric for metric in product_metrics(db_session) if metric["code"] == "LYNX")

    assert lynx["runs_total"] == 2
    assert lynx["events_total"] == 2
    assert lynx["cost_cents"] == 24
    assert lynx["units"] == 2
