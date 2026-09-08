from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import AuditLog
from app.staff.models import StaffMember, StaffMemberRole
from app.staff.roles import Department, StaffRole
from tests.auth.conftest import PlatformStub

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


def _staff_with_role(db_session: Session, role: StaffRole) -> StaffMember:
    staff = StaffMember(
        platform_user_id=uuid4(),
        display_name=f"{role.value} staff",
        department=Department.CODING,
        active=True,
    )
    db_session.add(staff)
    db_session.flush()
    db_session.add(StaffMemberRole(staff_member_id=staff.id, role=role))
    db_session.flush()
    return staff


async def _sign_in(
    client: httpx.AsyncClient, platform_stub: PlatformStub, staff: StaffMember, ticket: str
) -> str:
    platform_stub.exchange(ticket=ticket, audience="sift-os", subject=staff.platform_user_id)
    response = await client.post("/api/auth/sso/exchange", json={"ticket": ticket})
    assert response.status_code == 204
    return client.cookies["sift_os_csrf"]


async def test_coding_staff_cannot_read_staff_directory(
    client: httpx.AsyncClient, platform_stub: PlatformStub, db_session: Session
) -> None:
    coder = _staff_with_role(db_session, StaffRole.CODING)
    db_session.commit()
    await _sign_in(client, platform_stub, coder, "coder")

    response = await client.get("/api/staff")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


async def test_admin_can_change_roles_and_records_audit(
    client: httpx.AsyncClient, platform_stub: PlatformStub, db_session: Session
) -> None:
    admin = _staff_with_role(db_session, StaffRole.ADMIN)
    target = _staff_with_role(db_session, StaffRole.SALES)
    db_session.commit()
    csrf = await _sign_in(client, platform_stub, admin, "admin")

    response = await client.patch(
        f"/api/staff/{target.id}/roles",
        json={"roles": ["coding", "sales_lead"]},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200
    assert response.json()["roles"] == ["coding", "sales_lead"]
    audit = db_session.scalar(select(AuditLog).where(AuditLog.action == "staff.roles.updated"))
    assert audit is not None
    assert audit.actor_staff_id == admin.id
    assert audit.entity_id == target.id
    assert audit.previous == {"roles": ["sales"]}
    assert audit.new == {"roles": ["coding", "sales_lead"]}


@pytest.mark.parametrize("csrf_header", [None, "wrong"])
async def test_admin_role_change_requires_matching_csrf_token(
    csrf_header: str | None,
    client: httpx.AsyncClient,
    platform_stub: PlatformStub,
    db_session: Session,
) -> None:
    admin = _staff_with_role(db_session, StaffRole.ADMIN)
    target = _staff_with_role(db_session, StaffRole.SALES)
    db_session.commit()
    await _sign_in(client, platform_stub, admin, f"csrf-{csrf_header}")

    headers = {} if csrf_header is None else {"X-CSRF-Token": csrf_header}
    response = await client.patch(
        f"/api/staff/{target.id}/roles",
        json={"roles": ["coding"]},
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_INVALID"
    roles = set(
        db_session.scalars(
            select(StaffMemberRole.role).where(StaffMemberRole.staff_member_id == target.id)
        )
    )
    assert roles == {StaffRole.SALES}


async def test_admin_cannot_remove_last_active_admin(
    client: httpx.AsyncClient, platform_stub: PlatformStub, db_session: Session
) -> None:
    admin = _staff_with_role(db_session, StaffRole.ADMIN)
    db_session.commit()
    csrf = await _sign_in(client, platform_stub, admin, "last-admin")

    response = await client.patch(
        f"/api/staff/{admin.id}/roles",
        json={"roles": ["coding"]},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "LAST_PRIVILEGED_ROLE"
