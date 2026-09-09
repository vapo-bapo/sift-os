from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.integrations.schemas import ProductEventAccepted, ProductEventIn
from app.products.models import ProductEvent, ProductRun

TERMINAL_STATUSES = frozenset({"succeeded", "failed", "canceled"})


def _status_for_event(payload: ProductEventIn) -> str | None:
    if payload.status is not None:
        return payload.status.lower()
    suffix = payload.event_type.rsplit(".", 1)[-1]
    if suffix in {"completed", "succeeded"}:
        return "succeeded"
    if suffix == "failed":
        return "failed"
    if suffix in {"canceled", "cancelled"}:
        return "canceled"
    if suffix == "started":
        return "running"
    return None


def ingest_product_event(
    db: Session, *, product_id: UUID, payload: ProductEventIn
) -> ProductEventAccepted:
    existing = db.execute(
        select(ProductEvent.product_id, ProductEvent.product_run_id).where(
            ProductEvent.id == payload.event_id
        )
    ).one_or_none()
    if existing is not None:
        return ProductEventAccepted(
            event_id=payload.event_id,
            duplicate=True,
            product_id=existing[0],
            run_id=existing[1],
        )

    run: ProductRun | None = None
    if payload.external_run_id is not None:
        db.execute(
            insert(ProductRun)
            .values(
                product_id=product_id,
                external_run_id=payload.external_run_id,
                status="running",
                started_at=payload.occurred_at,
                event_count=0,
                cost_cents=0,
                units=0,
                run_metadata={},
            )
            .on_conflict_do_nothing(constraint="uq_product_external_run")
        )
        run = db.scalar(
            select(ProductRun)
            .where(
                ProductRun.product_id == product_id,
                ProductRun.external_run_id == payload.external_run_id,
            )
            .with_for_update()
        )
        if run is None:
            raise RuntimeError("product run could not be created")

    inserted = db.execute(
        insert(ProductEvent)
        .values(
            id=payload.event_id,
            product_id=product_id,
            product_run_id=run.id if run is not None else None,
            event_type=payload.event_type,
            schema_version=payload.schema_version,
            occurred_at=payload.occurred_at,
            received_at=datetime.now(UTC),
            external_run_id=payload.external_run_id,
            status=payload.status,
            cost_cents=payload.cost_cents,
            units=payload.units,
            payload=payload.payload,
        )
        .on_conflict_do_nothing(index_elements=[ProductEvent.id])
        .returning(ProductEvent.id)
    ).scalar_one_or_none()
    if inserted is None:
        duplicate = db.execute(
            select(ProductEvent.product_id, ProductEvent.product_run_id).where(
                ProductEvent.id == payload.event_id
            )
        ).one()
        return ProductEventAccepted(
            event_id=payload.event_id,
            duplicate=True,
            product_id=duplicate[0],
            run_id=duplicate[1],
        )

    if run is not None:
        run.event_count += 1
        run.cost_cents += payload.cost_cents
        run.units += payload.units
        if payload.occurred_at < run.started_at:
            run.started_at = payload.occurred_at
        next_status = _status_for_event(payload)
        if next_status is not None:
            run.status = next_status
        if run.status in TERMINAL_STATUSES:
            run.completed_at = payload.occurred_at
        incoming_metadata = payload.payload.get("run_metadata")
        if isinstance(incoming_metadata, dict):
            run.run_metadata = {
                **run.run_metadata,
                **cast(dict[str, object], incoming_metadata),
            }
        db.flush()

    return ProductEventAccepted(
        event_id=payload.event_id,
        duplicate=False,
        product_id=product_id,
        run_id=run.id if run is not None else None,
    )
