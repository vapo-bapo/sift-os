from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crm.models import AccountType, CrmAccount
from app.crm.schemas import CaseStudyMetricsUpdate
from app.crm.service import seed_case_studies, upsert_case_study_metrics
from tests.crm.test_service import _current

pytestmark = pytest.mark.integration


def test_case_study_seed_is_idempotent_and_contains_no_invented_metrics(
    db_session: Session,
) -> None:
    actor = _current(db_session, all_records=True)

    first = seed_case_studies(db_session, actor)
    db_session.flush()
    second = seed_case_studies(db_session, actor)
    db_session.flush()

    assert [account.name for account in first] == ["Stral", "Auris"]
    assert [account.id for account in second] == [account.id for account in first]
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(CrmAccount)
            .where(CrmAccount.account_type == AccountType.CASE_STUDY)
        )
        == 2
    )


def test_case_study_metrics_are_persisted_without_rounding(db_session: Session) -> None:
    actor = _current(db_session, all_records=True)
    account = seed_case_studies(db_session, actor)[0]
    db_session.flush()

    metrics = upsert_case_study_metrics(
        db_session,
        actor,
        account.id,
        CaseStudyMetricsUpdate(
            baseline={"manual_hours": 12},
            runs=30,
            leads=120,
            qualified=48,
            meetings=11,
            hours_saved=Decimal("19.75"),
            conversion=Decimal("40.0000"),
            notes="Verified customer data",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
        ),
    )
    db_session.flush()

    assert metrics.conversion == Decimal("40.0000")
    assert metrics.hours_saved == Decimal("19.75")
