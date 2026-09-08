import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.staff.models import StaffMember, StaffMemberRole
from app.staff.permissions import Permission, has_permission
from app.staff.roles import StaffRole
from app.staff.seed import STAFF_SEED, seed_staff


@pytest.mark.parametrize(
    ("role", "permission", "allowed"),
    [
        (StaffRole.ADMIN, Permission.FINANCE_READ, True),
        (StaffRole.SALES_LEAD, Permission.SALES_ASSIGN, True),
        (StaffRole.SALES, Permission.SALES_ASSIGN, False),
        (StaffRole.CODING, Permission.PRODUCT_READ, True),
        (StaffRole.CODING, Permission.FINANCE_READ, False),
    ],
)
def test_permission_matrix(role: StaffRole, permission: Permission, allowed: bool) -> None:
    assert has_permission({role}, permission) is allowed


@pytest.mark.integration
def test_staff_seed_is_idempotent_and_preserves_local_changes(db_session: Session) -> None:
    seed_staff(db_session)
    db_session.commit()

    first_count = db_session.scalar(select(func.count()).select_from(StaffMember))
    assert first_count == 8

    alessandro = db_session.scalar(
        select(StaffMember).where(StaffMember.platform_user_id == STAFF_SEED[0].platform_user_id)
    )
    assert alessandro is not None
    alessandro.active = False
    alessandro.display_name = "Old name"
    db_session.add(StaffMemberRole(staff_member_id=alessandro.id, role=StaffRole.SALES_LEAD))
    db_session.commit()

    seed_staff(db_session)
    db_session.commit()

    second_count = db_session.scalar(select(func.count()).select_from(StaffMember))
    roles = set(
        db_session.scalars(
            select(StaffMemberRole.role).where(StaffMemberRole.staff_member_id == alessandro.id)
        )
    )
    assert second_count == 8
    assert alessandro.display_name == "Alessandro Bellucco"
    assert alessandro.active is False
    assert roles == {StaffRole.CEO, StaffRole.ADMIN, StaffRole.CODING, StaffRole.SALES_LEAD}


@pytest.mark.integration
def test_staff_seed_creates_exact_platform_identities(db_session: Session) -> None:
    seed_staff(db_session)
    db_session.commit()

    platform_ids = set(db_session.scalars(select(StaffMember.platform_user_id)))

    assert platform_ids == {entry.platform_user_id for entry in STAFF_SEED}
