from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.orm import Session

from app.auth.models import UserSession
from app.auth.tokens import new_opaque_token, token_digest
from app.core.config import Settings
from app.staff.models import StaffMember, StaffMemberRole
from app.staff.roles import Department, StaffRole
from tests.auth.conftest import PlatformStub

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


async def _sign_in(
    client: httpx.AsyncClient, platform_stub: PlatformStub, staff: StaffMember
) -> None:
    platform_stub.exchange(ticket="valid", audience="sift-os", subject=staff.platform_user_id)
    response = await client.post("/api/auth/sso/exchange", json={"ticket": "valid"})
    assert response.status_code == 204


@pytest.fixture
def coding_staff(db_session: Session) -> StaffMember:
    staff = StaffMember(
        platform_user_id=uuid4(),
        display_name="Coding Staff",
        department=Department.CODING,
        active=True,
    )
    db_session.add(staff)
    db_session.flush()
    db_session.add(StaffMemberRole(staff_member_id=staff.id, role=StaffRole.CODING))
    db_session.flush()
    return staff


async def test_me_returns_authenticated_staff_and_frozen_permission_set(
    client: httpx.AsyncClient, platform_stub: PlatformStub, coding_staff: StaffMember
) -> None:
    await _sign_in(client, platform_stub, coding_staff)

    response = await client.get("/api/me")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(coding_staff.id),
        "display_name": "Coding Staff",
        "department": "coding",
        "roles": ["coding"],
        "permissions": [
            "dashboard:company",
            "objective:read",
            "product:read",
            "task:read",
            "task:write",
        ],
    }


async def test_inactive_staff_cannot_use_me_after_session_creation(
    client: httpx.AsyncClient,
    platform_stub: PlatformStub,
    coding_staff: StaffMember,
    db_session: Session,
) -> None:
    await _sign_in(client, platform_stub, coding_staff)
    coding_staff.active = False
    db_session.commit()

    response = await client.get("/api/me")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "STAFF_ACCESS_DENIED"


async def test_expired_session_cannot_use_me(
    client: httpx.AsyncClient,
    auth_settings: Settings,
    coding_staff: StaffMember,
    db_session: Session,
) -> None:
    raw_session = new_opaque_token()
    db_session.add(
        UserSession(
            staff_member_id=coding_staff.id,
            token_digest=token_digest(raw_session, auth_settings.session_secret),
            csrf_nonce_digest="a" * 64,
            platform_assertion_jti="expired-session",
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
    )
    db_session.commit()

    client.cookies.set("sift_os_session", raw_session)
    response = await client.get("/api/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "SESSION_INVALID"
