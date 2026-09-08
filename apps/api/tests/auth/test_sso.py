from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import UserSession
from app.staff.models import StaffMember
from app.staff.roles import Department

from .conftest import PlatformStub

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


async def test_staff_ticket_creates_local_session(
    client: httpx.AsyncClient,
    platform_stub: PlatformStub,
    active_staff: StaffMember,
    db_session: Session,
) -> None:
    platform_stub.exchange(
        ticket="valid", audience="sift-os", subject=active_staff.platform_user_id
    )

    response = await client.post("/api/auth/sso/exchange", json={"ticket": "valid"})

    assert response.status_code == 204
    assert response.cookies["sift_os_session"]
    assert response.cookies["sift_os_csrf"]
    set_cookie = response.headers.get_list("set-cookie")
    assert any("sift_os_session=" in value and "HttpOnly" in value for value in set_cookie)
    assert any("sift_os_csrf=" in value and "HttpOnly" not in value for value in set_cookie)
    stored = db_session.scalar(select(UserSession))
    assert stored is not None
    assert response.cookies["sift_os_session"] not in stored.token_digest
    assert response.cookies["sift_os_csrf"] not in stored.csrf_nonce_digest


async def test_non_staff_platform_user_is_forbidden(
    client: httpx.AsyncClient, platform_stub: PlatformStub
) -> None:
    platform_stub.exchange(ticket="valid", audience="sift-os", subject=uuid4())

    response = await client.post("/api/auth/sso/exchange", json={"ticket": "valid"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "STAFF_ACCESS_DENIED"


async def test_inactive_staff_is_forbidden(
    client: httpx.AsyncClient,
    platform_stub: PlatformStub,
    db_session: Session,
) -> None:
    member = StaffMember(
        platform_user_id=uuid4(),
        display_name="Inactive Staff",
        department=Department.SALES,
        active=False,
    )
    db_session.add(member)
    db_session.flush()
    platform_stub.exchange(ticket="valid", audience="sift-os", subject=member.platform_user_id)

    response = await client.post("/api/auth/sso/exchange", json={"ticket": "valid"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "STAFF_ACCESS_DENIED"


async def test_replayed_assertion_jti_is_rejected(
    client: httpx.AsyncClient, platform_stub: PlatformStub, active_staff: StaffMember
) -> None:
    platform_stub.exchange(
        ticket="one",
        audience="sift-os",
        subject=active_staff.platform_user_id,
        jti="same",
    )
    first = await client.post("/api/auth/sso/exchange", json={"ticket": "one"})
    assert first.status_code == 204
    platform_stub.exchange(
        ticket="two",
        audience="sift-os",
        subject=active_staff.platform_user_id,
        jti="same",
    )

    response = await client.post("/api/auth/sso/exchange", json={"ticket": "two"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ASSERTION_REPLAYED"


@pytest.mark.parametrize("claim", ["issuer", "audience", "expiry", "signature"])
async def test_invalid_platform_assertion_is_rejected_without_secret_material(
    claim: str,
    client: httpx.AsyncClient,
    platform_stub: PlatformStub,
    active_staff: StaffMember,
) -> None:
    kwargs: dict[str, object] = {}
    if claim == "issuer":
        kwargs["issuer"] = "http://attacker.test"
    elif claim == "audience":
        kwargs["audience"] = "another-product"
    elif claim == "expiry":
        kwargs["expires_at"] = datetime.now(UTC) - timedelta(seconds=1)
    elif claim == "signature":
        kwargs["key"] = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    platform_stub.exchange(
        ticket="sensitive-ticket-value",
        audience=str(kwargs.pop("audience", "sift-os")),
        subject=active_staff.platform_user_id,
        **kwargs,
    )

    response = await client.post(
        "/api/auth/sso/exchange", json={"ticket": "sensitive-ticket-value"}
    )

    assert response.status_code == 401
    body = response.text
    assert "sensitive-ticket-value" not in body
    assert platform_stub.tickets["sensitive-ticket-value"] not in body
