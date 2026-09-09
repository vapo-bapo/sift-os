from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import UserSession
from app.core.errors import ApiError
from app.crm.models import (
    AccountType,
    CrmAccount,
    CrmActivity,
    CrmContact,
    CrmOpportunity,
    OpportunityStage,
    OpportunityStageHistory,
)
from app.crm.schemas import (
    AccountCreate,
    AccountUpdate,
    ActivityCreate,
    ContactCreate,
    ContactUpdate,
    OpportunityCreate,
)
from app.crm.service import (
    change_opportunity_stage,
    create_account,
    create_activity,
    create_contact,
    create_opportunity,
    list_accounts,
    update_account,
    update_contact,
)
from app.staff.dependencies import CurrentStaff
from app.staff.models import StaffMember
from app.staff.permissions import Permission
from app.staff.roles import Department, StaffRole

pytestmark = pytest.mark.integration


def _current(db: Session, *, all_records: bool = False) -> CurrentStaff:
    staff = StaffMember(
        platform_user_id=uuid4(),
        display_name="Sales person",
        department=Department.SALES,
        active=True,
    )
    db.add(staff)
    db.flush()
    session = UserSession(
        staff_member_id=staff.id,
        token_digest=uuid4().hex,
        csrf_nonce_digest=uuid4().hex,
        platform_assertion_jti=uuid4().hex,
        expires_at=datetime.max.replace(tzinfo=UTC),
    )
    db.add(session)
    db.flush()
    permissions = (
        frozenset({Permission.SALES_READ_ALL, Permission.SALES_WRITE_ALL, Permission.SALES_ASSIGN})
        if all_records
        else frozenset({Permission.SALES_READ_OWN, Permission.SALES_WRITE_OWN})
    )
    return CurrentStaff(
        session=session,
        staff=staff,
        roles=frozenset({StaffRole.SALES_LEAD if all_records else StaffRole.SALES}),
        permissions=permissions,
    )


def test_sales_list_is_scoped_to_owned_accounts(db_session: Session) -> None:
    actor = _current(db_session)
    other = _current(db_session)
    create_account(db_session, actor, AccountCreate(name="Mine"))
    create_account(db_session, other, AccountCreate(name="Not mine"))
    db_session.flush()

    items, total = list_accounts(db_session, actor, page=1, page_size=20)

    assert total == 1
    assert [item.name for item in items] == ["Mine"]


def test_account_domain_is_normalized_and_duplicate_is_rejected(db_session: Session) -> None:
    actor = _current(db_session, all_records=True)
    account = create_account(
        db_session,
        actor,
        AccountCreate(
            name="Acme",
            domain="https://WWW.Acme.test/about",
            account_type=AccountType.DIRECT_PROSPECT,
        ),
    )
    db_session.flush()
    assert account.normalized_domain == "acme.test"

    with pytest.raises(ApiError) as caught:
        create_account(
            db_session,
            actor,
            AccountCreate(name="Acme duplicate", domain="ACME.test"),
        )

    assert caught.value.status_code == 409
    assert caught.value.code == "CRM_ACCOUNT_DUPLICATE"


def test_account_domain_can_be_cleared(db_session: Session) -> None:
    actor = _current(db_session)
    first = create_account(db_session, actor, AccountCreate(name="Acme", domain="acme.test"))
    create_account(db_session, actor, AccountCreate(name="No domain"))
    db_session.flush()

    updated = update_account(db_session, actor, first.id, AccountUpdate(domain=None))

    assert updated.domain is None
    assert updated.normalized_domain is None


def test_contact_duplicate_email_is_rejected(db_session: Session) -> None:
    actor = _current(db_session)
    account = create_account(db_session, actor, AccountCreate(name="Acme"))
    db_session.flush()
    create_contact(
        db_session,
        actor,
        ContactCreate(
            account_id=account.id, first_name="Ada", last_name="Lovelace", email="ADA@EXAMPLE.COM"
        ),
    )
    db_session.flush()

    with pytest.raises(ApiError) as caught:
        create_contact(
            db_session,
            actor,
            ContactCreate(
                account_id=account.id, first_name="Ada", last_name="Byron", email="ada@example.com"
            ),
        )

    assert caught.value.code == "CRM_CONTACT_DUPLICATE"


def test_contact_without_email_or_phone_can_be_updated(db_session: Session) -> None:
    actor = _current(db_session)
    account = create_account(db_session, actor, AccountCreate(name="Acme"))
    db_session.flush()
    first = create_contact(
        db_session,
        actor,
        ContactCreate(account_id=account.id, first_name="Ada", last_name="Lovelace"),
    )
    create_contact(
        db_session,
        actor,
        ContactCreate(account_id=account.id, first_name="Grace", last_name="Hopper"),
    )
    db_session.flush()

    updated = update_contact(db_session, actor, first.id, ContactUpdate(role="CTO"))

    assert updated.role == "CTO"


def test_stage_transition_is_written_to_append_only_history(db_session: Session) -> None:
    actor = _current(db_session)
    account = create_account(db_session, actor, AccountCreate(name="Acme"))
    db_session.flush()
    opportunity = create_opportunity(
        db_session,
        actor,
        OpportunityCreate(
            account_id=account.id,
            estimated_value_cents=100_00,
            probability=30,
        ),
    )
    db_session.flush()

    change_opportunity_stage(db_session, actor, opportunity.id, OpportunityStage.WON)
    db_session.flush()

    history = list(
        db_session.scalars(
            select(OpportunityStageHistory)
            .where(OpportunityStageHistory.opportunity_id == opportunity.id)
            .order_by(OpportunityStageHistory.created_at)
        )
    )
    assert [(row.previous_stage, row.new_stage) for row in history] == [
        (None, OpportunityStage.PROSPECT),
        (OpportunityStage.PROSPECT, OpportunityStage.WON),
    ]
    assert opportunity.weighted_value_cents == 3_000
    assert opportunity.won_at is not None


def test_sales_cannot_attach_activity_to_another_owners_contact(db_session: Session) -> None:
    actor = _current(db_session)
    other = _current(db_session)
    account = create_account(db_session, other, AccountCreate(name="Private account"))
    db_session.flush()
    contact = create_contact(
        db_session,
        other,
        ContactCreate(account_id=account.id, first_name="Private", last_name="Lead"),
    )
    db_session.flush()

    with pytest.raises(ApiError) as caught:
        create_activity(
            db_session,
            actor,
            ActivityCreate(
                contact_id=contact.id,
                activity_type="call",
                started_at=datetime.now(UTC),
            ),
        )

    assert caught.value.code == "CRM_RECORD_FORBIDDEN"


def test_completed_activity_can_create_follow_up_atomically(db_session: Session) -> None:
    actor = _current(db_session)
    account = create_account(db_session, actor, AccountCreate(name="Acme"))
    db_session.flush()
    follow_up_at = datetime(2026, 9, 10, 9, tzinfo=UTC)

    create_activity(
        db_session,
        actor,
        ActivityCreate(
            account_id=account.id,
            activity_type="call",
            started_at=datetime(2026, 9, 9, 9, tzinfo=UTC),
            completed_at=datetime(2026, 9, 9, 9, 15, tzinfo=UTC),
            next_action="Call again",
            next_action_at=follow_up_at,
            create_follow_up=True,
        ),
    )
    db_session.flush()

    activities = list(db_session.scalars(select(CrmActivity).order_by(CrmActivity.started_at)))
    assert len(activities) == 2
    assert activities[1].activity_type.value == "follow_up"
    assert activities[1].started_at == follow_up_at
    assert activities[1].completed_at is None


def test_models_use_the_expected_native_tables() -> None:
    assert CrmAccount.__tablename__ == "crm_accounts"
    assert CrmContact.__tablename__ == "crm_contacts"
    assert CrmOpportunity.__tablename__ == "crm_opportunities"
