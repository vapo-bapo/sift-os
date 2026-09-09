from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.integrations.schemas import ProductEventIn
from app.products.seed import PRODUCT_SEEDS


@pytest.mark.unit
def test_product_catalog_contains_only_real_initial_products() -> None:
    assert [(product.code, product.name) for product in PRODUCT_SEEDS] == [
        ("ARGUS", "ARGUS"),
        ("LYNX", "LYNX"),
    ]


@pytest.mark.unit
def test_event_type_is_flexible_but_must_be_namespaced_and_cost_is_cents() -> None:
    event = ProductEventIn(
        event_id=uuid4(),
        event_type="document.analysis.completed",
        occurred_at=datetime.now(UTC),
        external_run_id="run-42",
        status="succeeded",
        cost_cents=37,
        units=12,
        payload={"documents": 3},
    )

    assert event.event_type == "document.analysis.completed"
    assert event.cost_cents == 37


@pytest.mark.unit
@pytest.mark.parametrize("event_type", ["bad type", "UPPER", "x", ".started"])
def test_invalid_event_type_is_rejected(event_type: str) -> None:
    with pytest.raises(ValidationError):
        ProductEventIn(
            event_id=uuid4(),
            event_type=event_type,
            occurred_at=datetime.now(UTC),
        )


@pytest.mark.unit
def test_event_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        ProductEventIn(
            event_id=uuid4(),
            event_type="run.started",
            occurred_at=datetime.now(),
        )
