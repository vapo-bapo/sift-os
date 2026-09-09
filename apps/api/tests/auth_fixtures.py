from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy.orm import Session

from app.auth import routes
from app.core.config import Settings
from app.db.session import get_db
from app.main import create_app
from app.staff.models import StaffMember
from app.staff.roles import Department


@dataclass
class PlatformStub:
    private_key: rsa.RSAPrivateKey
    tickets: dict[str, str] = field(default_factory=dict)

    def exchange(
        self,
        *,
        ticket: str,
        audience: str,
        subject: UUID,
        issuer: str = "http://platform.test/",
        jti: str | None = None,
        expires_at: datetime | None = None,
        key: rsa.RSAPrivateKey | None = None,
    ) -> None:
        now = datetime.now(UTC)
        self.tickets[ticket] = jwt.encode(
            {
                "iss": issuer,
                "aud": audience,
                "sub": str(subject),
                "product_id": str(uuid4()),
                "entitlement_id": str(uuid4()),
                "iat": int(now.timestamp()),
                "exp": int((expires_at or now + timedelta(minutes=5)).timestamp()),
                "jti": jti or uuid4().hex,
            },
            key or self.private_key,
            algorithm="RS256",
            headers={"kid": "platform-test-key"},
        )

    async def exchange_ticket(self, ticket: str, settings: Settings) -> str:
        del settings
        return self.tickets[ticket]


@pytest.fixture
def auth_settings(test_database_url: str) -> Settings:
    return Settings(
        APP_ENV="test",
        DATABASE_URL=test_database_url,
        SIFT_PLATFORM_PUBLIC_URL="http://platform.test",
        SIFT_PLATFORM_SSO_ISSUER="http://platform.test",
        SIFT_PLATFORM_JWKS_URL="http://platform.test/.well-known/jwks.json",
    )


@pytest.fixture
def platform_stub() -> PlatformStub:
    return PlatformStub(rsa.generate_private_key(public_exponent=65537, key_size=2048))


@pytest.fixture
def active_staff(db_session: Session) -> StaffMember:
    member = StaffMember(
        platform_user_id=uuid4(),
        display_name="Active Staff",
        department=Department.CODING,
        active=True,
    )
    db_session.add(member)
    db_session.flush()
    return member


@pytest.fixture
async def client(
    db_session: Session,
    auth_settings: Settings,
    platform_stub: PlatformStub,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[httpx.AsyncClient]:
    app = create_app(auth_settings)

    def override_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.state.platform_jwks = SimpleNamespace(
        get_signing_key_from_jwt=lambda token: SimpleNamespace(
            key=platform_stub.private_key.public_key()
        )
    )
    monkeypatch.setattr(routes, "exchange_platform_ticket", platform_stub.exchange_ticket)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
