from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.partners.models import PartnerStatus
from app.partners.schemas import AgreementCreate, PartnerClientCreate, PartnerCreate
from app.partners.service import attribute_client, create_agreement, create_partner
from app.staff.models import StaffMember
from app.staff.roles import Department


@pytest.mark.integration
def test_first_attributed_client_activates_partner_and_persists_exact_split(
    db_session: Session,
) -> None:
    staff = StaffMember(
        platform_user_id=uuid4(),
        display_name="Partner Lead",
        department=Department.SALES,
        active=True,
    )
    db_session.add(staff)
    db_session.flush()
    partner = create_partner(
        db_session,
        PartnerCreate(name="Example Partner", owner_staff_id=staff.id),
    )
    create_agreement(
        db_session,
        partner=partner,
        actor_id=staff.id,
        payload=AgreementCreate(
            effective_from=datetime(2026, 1, 1, tzinfo=UTC),
            partner_share_bps=2_000,
            sift_share_bps=8_000,
        ),
    )

    client = attribute_client(
        db_session,
        partner=partner,
        payload=PartnerClientCreate(
            external_client_id=uuid4(),
            client_name="Real Customer Reference",
            attributed_at=datetime(2026, 9, 9, tzinfo=UTC),
            gross_revenue_cents=101,
        ),
    )

    assert client.partner_share_cents == 20
    assert client.sift_share_cents == 81
    assert partner.status == PartnerStatus.ACTIVE
    assert partner.activated_at == datetime(2026, 9, 9, tzinfo=UTC)
    assert db_session.scalar(select(StaffMember).where(StaffMember.id == staff.id)) is staff
