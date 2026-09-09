from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.crm.models import OpportunityStage
from app.crm.schemas import AccountCreate, CaseStudyMetricsUpdate, OpportunityCreate


@pytest.mark.unit
def test_account_requires_a_real_name() -> None:
    with pytest.raises(ValidationError):
        AccountCreate(name="   ")


@pytest.mark.unit
def test_opportunity_calculates_weighted_value() -> None:
    payload = OpportunityCreate(
        account_id="a32297c7-4ac8-42e8-ae36-f524b1b4d64b",
        owner_id="5c60ddea-f1dd-4281-9f2a-ac8ebaa50a72",
        stage=OpportunityStage.QUALIFIED,
        estimated_value_cents=125_00,
        probability=40,
        expected_close_date=date.today(),
    )

    assert payload.weighted_value_cents == 5_000


@pytest.mark.unit
def test_opportunity_rejects_invalid_probability() -> None:
    with pytest.raises(ValidationError):
        OpportunityCreate(
            account_id="a32297c7-4ac8-42e8-ae36-f524b1b4d64b",
            owner_id="5c60ddea-f1dd-4281-9f2a-ac8ebaa50a72",
            estimated_value_cents=100,
            probability=101,
        )


@pytest.mark.unit
def test_schema_does_not_accept_client_managed_timestamps() -> None:
    payload = AccountCreate(name="Acme", created_at=datetime.now())
    assert not hasattr(payload, "created_at")


@pytest.mark.unit
def test_case_study_period_cannot_end_before_it_starts() -> None:
    with pytest.raises(ValidationError):
        CaseStudyMetricsUpdate(period_start=date(2026, 2, 1), period_end=date(2026, 1, 1))
