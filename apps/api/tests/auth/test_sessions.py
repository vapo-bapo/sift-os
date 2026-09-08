import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import AuditLog
from app.auth.models import UserSession
from app.staff.models import StaffMember

from .conftest import PlatformStub

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


async def _sign_in(
    client: httpx.AsyncClient, platform_stub: PlatformStub, active_staff: StaffMember
) -> None:
    platform_stub.exchange(
        ticket="valid", audience="sift-os", subject=active_staff.platform_user_id
    )
    response = await client.post("/api/auth/sso/exchange", json={"ticket": "valid"})
    assert response.status_code == 204


async def test_logout_requires_matching_csrf_header(
    client: httpx.AsyncClient, platform_stub: PlatformStub, active_staff: StaffMember
) -> None:
    await _sign_in(client, platform_stub, active_staff)

    response = await client.post("/api/logout")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_INVALID"


async def test_logout_revokes_session_clears_cookies_and_records_audit(
    client: httpx.AsyncClient,
    platform_stub: PlatformStub,
    active_staff: StaffMember,
    db_session: Session,
) -> None:
    await _sign_in(client, platform_stub, active_staff)
    csrf = client.cookies["sift_os_csrf"]

    response = await client.post("/api/logout", headers={"X-CSRF-Token": csrf})

    assert response.status_code == 204
    assert "sift_os_session" not in client.cookies
    assert "sift_os_csrf" not in client.cookies
    session = db_session.scalar(select(UserSession))
    assert session is not None and session.revoked_at is not None
    audit = db_session.scalar(select(AuditLog).where(AuditLog.action == "auth.logout"))
    assert audit is not None
    assert audit.actor_staff_id == active_staff.id


async def test_logout_rejects_csrf_header_that_does_not_match_cookie(
    client: httpx.AsyncClient, platform_stub: PlatformStub, active_staff: StaffMember
) -> None:
    await _sign_in(client, platform_stub, active_staff)

    response = await client.post("/api/logout", headers={"X-CSRF-Token": "wrong"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_INVALID"
