# SIFT OS Foundation and Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver an independently runnable SIFT OS foundation with PostgreSQL migrations, Platform SSO, local secure sessions, explicit eight-person staff mapping, backend RBAC, role-aware shell, CI, Docker, and security documentation.

**Architecture:** A React/Vite web service proxies same-origin `/api` traffic to a modular FastAPI service backed by a dedicated PostgreSQL database. SIFT Platform remains the identity authority: SIFT OS exchanges its existing one-time ticket, verifies the RS256 assertion via JWKS, then creates an opaque local session only for an active `staff_members.platform_user_id` match.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL 17, psycopg 3, pytest 9, React 19, TypeScript 5.9, Vite 8, React Router 7, TanStack Query 5, Vitest 4, Playwright, Docker, GitHub Actions.

## Global Constraints

- SIFT Platform is the only source of truth for identity, passwords, customer accounts, licenses, and product entitlement.
- Never copy password hashes, authenticate by email domain, or store an SSO assertion in `localStorage`.
- PostgreSQL is mandatory in every integration environment; tests use a database whose name ends in `_test`.
- Store timestamps in UTC and exposed primary keys as UUID.
- Production authentication uses `Secure`, `HttpOnly`, `SameSite=Lax` cookies and CSRF for mutations.
- Production CORS allows exact origins only; no wildcard is permitted.
- Backend authorization is deny-by-default and combines role, permission, department, and ownership.
- The ninth Platform account `Aliceg76` is not staff and must receive `403` even when directly opening SIFT OS.
- Do not commit secrets or create production data with invented email addresses.
- Match the SIFT Platform cream/sand/ink/gold design language and keep the UI dense, legible, and keyboard-friendly.
- Do not use `create_all()` as a production migration mechanism.

---

## File map

The foundation creates these responsibility boundaries:

- `apps/api/app/main.py`: FastAPI composition only.
- `apps/api/app/core/config.py`: validated environment configuration.
- `apps/api/app/core/errors.py`: stable API error contract.
- `apps/api/app/core/middleware.py`: request ID and safe structured access logging.
- `apps/api/app/db/{base,session}.py`: SQLAlchemy metadata and session lifecycle.
- `apps/api/app/auth/{models,tokens,csrf,sso,service,dependencies,routes,schemas}.py`: SSO exchange, local sessions, CSRF, and current-user resolution.
- `apps/api/app/staff/{models,roles,service,dependencies,routes,schemas,seed}.py`: explicit staff mapping and RBAC.
- `apps/api/app/audit/{models,service}.py`: append-only critical-action recording.
- `apps/api/migrations/`: Alembic environment and schema revisions.
- `apps/web/src/app/`: router, providers, and query client.
- `apps/web/src/features/auth/`: SSO callback, `/me`, logout, and guards.
- `apps/web/src/components/`: shared brand and role-aware shell.
- `apps/web/src/pages/`: callback, access-denied, and role landing pages.
- `apps/web/src/styles/`: tokens and shell styles derived from Platform.
- `deploy/`, `Dockerfile.api`, `Dockerfile.web`, `docker-compose.yml`: deterministic local and Railway runtime.
- `.github/workflows/ci.yml`: backend, frontend, migrations, and container verification.

### Task 1: Repository foundation and deterministic toolchains

**Files:**
- Create: `.gitignore`
- Create: `.editorconfig`
- Create: `.env.example`
- Create: `pyproject.toml`
- Create: `package.json`
- Create: `apps/api/app/__init__.py`
- Create: `apps/api/tests/__init__.py`
- Create: `apps/web/package.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/tsconfig.app.json`
- Create: `apps/web/vite.config.ts`
- Create: `apps/web/index.html`
- Create: `apps/web/src/main.tsx`
- Test: `apps/api/tests/test_toolchain.py`
- Test: `apps/web/src/test/toolchain.test.ts`

**Interfaces:**
- Consumes: the approved design and version families already proven by SIFT Platform.
- Produces: `pytest`, `ruff`, `mypy`, `npm run lint`, `npm run typecheck`, `npm test`, and `npm run build` entry points used by all later tasks.

- [ ] **Step 1: Write failing toolchain tests**

```python
# apps/api/tests/test_toolchain.py
from app import __version__


def test_package_version_is_declared() -> None:
    assert __version__ == "0.1.0"
```

```ts
// apps/web/src/test/toolchain.test.ts
import { describe, expect, it } from "vitest";

describe("toolchain", () => {
  it("runs TypeScript tests", () => expect("sift-os").toContain("sift"));
});
```

- [ ] **Step 2: Run the tests to verify the missing foundation fails**

Run: `python3.12 -m pytest apps/api/tests/test_toolchain.py -v`

Expected: FAIL because `app` is not importable.

Run: `npm --prefix apps/web test -- --run`

Expected: FAIL because `apps/web/package.json` does not exist.

- [ ] **Step 3: Create the root Python and Node manifests**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=80"]
build-backend = "setuptools.build_meta"

[project]
name = "sift-os-api"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
  "alembic>=1.17,<2", "fastapi>=0.120,<1", "httpx>=0.28,<1",
  "psycopg[binary]>=3.2,<4", "pydantic-settings>=2.11,<3",
  "pyjwt[crypto]>=2.10,<3", "sqlalchemy>=2.0.44,<3",
  "structlog>=25.4,<26", "uvicorn[standard]>=0.38,<1",
]

[project.optional-dependencies]
dev = ["mypy>=1.18,<2", "pytest>=9,<10", "pytest-cov>=7,<8", "ruff>=0.14,<1"]

[tool.setuptools]
package-dir = {"" = "apps/api"}

[tool.setuptools.packages.find]
where = ["apps/api"]

[tool.pytest.ini_options]
testpaths = ["apps/api/tests"]
pythonpath = ["apps/api"]
addopts = "--strict-config --strict-markers"
markers = ["unit: database-independent tests", "integration: PostgreSQL-backed tests"]

[tool.ruff]
target-version = "py312"
line-length = 100
src = ["apps/api"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]

[tool.mypy]
python_version = "3.12"
strict = true
packages = ["app"]
mypy_path = "apps/api"
plugins = ["pydantic.mypy", "sqlalchemy.ext.mypy.plugin"]
```

```json
// package.json
{"name":"sift-os","private":true,"workspaces":["apps/web"],"scripts":{"web":"npm --workspace apps/web"}}
```

```json
// apps/web/package.json
{
  "name":"@sift/os-web","private":true,"version":"0.1.0","type":"module",
  "scripts":{"dev":"vite","lint":"eslint .","typecheck":"tsc -b --pretty false","test":"vitest","build":"tsc -b && vite build"},
  "dependencies":{"@tanstack/react-query":"^5.90.0","react":"^19.2.0","react-dom":"^19.2.0","react-router-dom":"^7.9.0"},
  "devDependencies":{"@eslint/js":"^9.39.0","@playwright/test":"^1.56.0","@testing-library/jest-dom":"^6.9.0","@testing-library/react":"^16.3.0","@types/node":"^24.10.0","@types/react":"^19.2.0","@types/react-dom":"^19.2.0","@vitejs/plugin-react":"^5.1.0","eslint":"^9.39.0","typescript":"~5.9.0","typescript-eslint":"^8.46.0","vite":"^8.2.0","vitest":"^4.1.0","jsdom":"^27.1.0"}
}
```

- [ ] **Step 4: Add configuration files and package marker**

```python
# apps/api/app/__init__.py
__version__ = "0.1.0"
```

```env
# .env.example
APP_ENV=development
DATABASE_URL=postgresql+psycopg://sift_os:sift_os@localhost:5433/sift_os
SIFT_OS_PUBLIC_URL=http://localhost:5173
SIFT_PLATFORM_PUBLIC_URL=http://localhost:8000
SIFT_PLATFORM_SSO_AUDIENCE=sift-os
SIFT_PLATFORM_SSO_ISSUER=http://localhost:8000
SIFT_PLATFORM_JWKS_URL=http://localhost:8000/.well-known/jwks.json
SESSION_SECRET=
CSRF_SECRET=
COOKIE_DOMAIN=
CORS_ALLOWED_ORIGINS=http://localhost:5173
LOG_LEVEL=INFO
```

Create TypeScript configs with `strict: true`, JSX `react-jsx`, DOM libraries, and `noEmit: true`; configure Vitest for `jsdom`; render a temporary `<div>SIFT OS</div>` from `src/main.tsx`. Add `.env`, virtualenvs, caches, `node_modules`, build output, coverage, OS metadata, and Playwright artifacts to `.gitignore`.

- [ ] **Step 5: Install and verify the toolchains**

Run: `python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]' && npm install`

Expected: dependency installation succeeds and creates committed lockfiles (`package-lock.json`; pinned Python ranges remain in `pyproject.toml`).

Run: `.venv/bin/pytest apps/api/tests/test_toolchain.py -v && npm --prefix apps/web test -- --run`

Expected: 2 tests PASS.

- [ ] **Step 6: Commit the foundation**

```bash
git add .gitignore .editorconfig .env.example pyproject.toml package.json package-lock.json apps
git commit -m "chore: initialize SIFT OS toolchains"
```

### Task 2: API configuration, health, errors, and request logging

**Files:**
- Create: `apps/api/app/core/config.py`
- Create: `apps/api/app/core/errors.py`
- Create: `apps/api/app/core/middleware.py`
- Create: `apps/api/app/core/logging.py`
- Create: `apps/api/app/api/health.py`
- Create: `apps/api/app/main.py`
- Test: `apps/api/tests/api/test_health.py`
- Test: `apps/api/tests/core/test_config.py`

**Interfaces:**
- Consumes: environment names from `.env.example`.
- Produces: `Settings`, `ApiError`, `RequestIdMiddleware`, `create_app()`, `GET /health`, and `GET /ready`.

- [ ] **Step 1: Write failing health and production-safety tests**

```python
def test_health_and_ready_are_distinct(client) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json() == {"status": "ready"}


def test_production_rejects_http_and_short_secrets() -> None:
    with pytest.raises(ValidationError):
        Settings(APP_ENV="production", SIFT_OS_PUBLIC_URL="http://os.example", SESSION_SECRET="x")
```

- [ ] **Step 2: Verify tests fail**

Run: `.venv/bin/pytest apps/api/tests/api/test_health.py apps/api/tests/core/test_config.py -v`

Expected: FAIL because `create_app` and `Settings` do not exist.

- [ ] **Step 3: Implement validated settings and API composition**

```python
class Settings(BaseSettings):
    app_env: Literal["development", "test", "staging", "production"] = "development"
    database_url: str = "postgresql+psycopg://sift_os:sift_os@localhost:5433/sift_os"
    sift_os_public_url: AnyHttpUrl = AnyHttpUrl("http://localhost:5173")
    sift_platform_public_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8000")
    sift_platform_sso_audience: str = "sift-os"
    sift_platform_sso_issuer: AnyHttpUrl = AnyHttpUrl("http://localhost:8000")
    sift_platform_jwks_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8000/.well-known/jwks.json")
    session_secret: SecretStr = SecretStr("local-development-session-secret-change-me")
    csrf_secret: SecretStr = SecretStr("local-development-csrf-secret-change-me")
    cors_allowed_origins: tuple[AnyHttpUrl, ...] = (AnyHttpUrl("http://localhost:5173"),)
    session_cookie_name: str = "sift_os_session"
    csrf_cookie_name: str = "sift_os_csrf"
    session_ttl_hours: int = 12

    @model_validator(mode="after")
    def secure_deployment(self) -> "Settings":
        if self.app_env in {"staging", "production"}:
            if self.sift_os_public_url.scheme != "https":
                raise ValueError("SIFT_OS_PUBLIC_URL must use HTTPS")
            if len(self.session_secret.get_secret_value()) < 32:
                raise ValueError("SESSION_SECRET must contain at least 32 characters")
        return self
```

```python
def create_app(settings: Settings | None = None, readiness_probe: Callable[[], bool] = lambda: True) -> FastAPI:
    app = FastAPI(title="SIFT OS API", version="0.1.0")
    app.state.settings = settings or get_settings()
    app.state.readiness_probe = readiness_probe
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health_router)
    return app
```

`RequestIdMiddleware` accepts a valid inbound `X-Request-ID` or creates a UUID, measures duration, returns the header, and logs only method, route template, status, duration, request ID, environment, and authenticated Platform ID when later available. `ApiError` serializes `{error:{code,message,details},request_id}` without stack traces.

- [ ] **Step 4: Run focused checks**

Run: `.venv/bin/pytest apps/api/tests/api/test_health.py apps/api/tests/core/test_config.py -v && .venv/bin/ruff check apps/api && .venv/bin/mypy apps/api/app`

Expected: all tests and static checks PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api
git commit -m "feat(api): add secure application foundation"
```

### Task 3: PostgreSQL metadata, staff, audit, sessions, and initial migration

**Files:**
- Create: `apps/api/app/db/base.py`
- Create: `apps/api/app/db/session.py`
- Create: `apps/api/app/staff/models.py`
- Create: `apps/api/app/staff/roles.py`
- Create: `apps/api/app/auth/models.py`
- Create: `apps/api/app/audit/models.py`
- Create: `apps/api/app/audit/service.py`
- Create: `apps/api/alembic.ini`
- Create: `apps/api/migrations/env.py`
- Create: `apps/api/migrations/versions/20260908_0001_identity_foundation.py`
- Test: `apps/api/tests/db/test_migrations.py`
- Test: `apps/api/tests/staff/test_models.py`

**Interfaces:**
- Consumes: `Settings.database_url`.
- Produces: `Base`, `get_db()`, `StaffMember`, `StaffRole`, `StaffMemberRole`, `UserSession`, `AuditLog`, and an Alembic head migration.

- [ ] **Step 1: Write failing migration and constraint tests**

```python
@pytest.mark.integration
def test_upgrade_head_creates_identity_tables(test_database_url: str) -> None:
    run_alembic(test_database_url, "upgrade", "head")
    assert {"staff_members", "staff_member_roles", "user_sessions", "audit_logs"} <= table_names(test_database_url)


@pytest.mark.integration
def test_platform_user_id_is_unique(db_session) -> None:
    db_session.add_all([staff(platform_user_id=PLATFORM_ID), staff(platform_user_id=PLATFORM_ID)])
    with pytest.raises(IntegrityError):
        db_session.flush()
```

- [ ] **Step 2: Verify the database tests fail against an isolated PostgreSQL database**

Run: `TEST_DATABASE_URL=postgresql+psycopg://sift_os:sift_os@localhost:5433/sift_os_test .venv/bin/pytest apps/api/tests/db/test_migrations.py apps/api/tests/staff/test_models.py -v`

Expected: FAIL because no Alembic revision or models exist.

- [ ] **Step 3: Implement focused models**

```python
class StaffMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "staff_members"
    platform_user_id: Mapped[UUID] = mapped_column(Uuid, unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(201), nullable=False)
    department: Mapped[Department] = mapped_column(enum_type(Department, "department"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class StaffMemberRole(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "staff_member_roles"
    __table_args__ = (UniqueConstraint("staff_member_id", "role", name="uq_staff_role"),)
    staff_member_id: Mapped[UUID] = mapped_column(ForeignKey("staff_members.id", ondelete="CASCADE"))
    role: Mapped[StaffRole] = mapped_column(enum_type(StaffRole, "staff_role"), nullable=False)


class UserSession(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "user_sessions"
    staff_member_id: Mapped[UUID] = mapped_column(ForeignKey("staff_members.id", ondelete="CASCADE"), index=True)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    csrf_nonce_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    platform_assertion_jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

`AuditLog` contains actor staff ID, action, entity type/ID, UTC timestamp, previous/new JSONB, request ID, IP, user-agent summary, and result. Its application service exposes only `record_audit_log(...)`; no update/delete repository is created.

- [ ] **Step 4: Write the explicit Alembic revision**

The revision creates PostgreSQL enum types, the four tables, foreign keys, unique constraints, and indexes. `downgrade()` drops tables in dependency order and enum types last. `apps/api/migrations/env.py` imports the model modules and uses `Base.metadata`; application startup never invokes `Base.metadata.create_all()`.

- [ ] **Step 5: Verify upgrade, downgrade, and models**

Run: `TEST_DATABASE_URL=postgresql+psycopg://sift_os:sift_os@localhost:5433/sift_os_test .venv/bin/pytest apps/api/tests/db/test_migrations.py apps/api/tests/staff/test_models.py -v`

Expected: migration upgrade/downgrade/upgrade and uniqueness tests PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/db apps/api/app/staff apps/api/app/auth/models.py apps/api/app/audit apps/api/alembic.ini apps/api/migrations apps/api/tests
git commit -m "feat(db): add identity and audit schema"
```

### Task 4: Platform SSO exchange and cryptographic verification

**Files:**
- Create: `apps/api/app/auth/schemas.py`
- Create: `apps/api/app/auth/sso.py`
- Create: `apps/api/app/auth/tokens.py`
- Create: `apps/api/app/auth/csrf.py`
- Create: `apps/api/app/auth/service.py`
- Create: `apps/api/app/auth/routes.py`
- Test: `apps/api/tests/auth/test_sso.py`
- Test: `apps/api/tests/auth/test_sessions.py`

**Interfaces:**
- Consumes: Platform `POST /api/v1/sso/exchange`, Platform JWKS, `StaffMember`, and `UserSession`.
- Produces: `POST /api/auth/sso/exchange`, `POST /api/logout`, `exchange_platform_ticket()`, `verify_platform_assertion()`, and opaque session/CSRF cookies.

- [ ] **Step 1: Write failing SSO security tests**

```python
@pytest.mark.integration
def test_staff_ticket_creates_local_session(client, platform_stub, active_staff) -> None:
    platform_stub.exchange(ticket="valid", audience="sift-os", subject=active_staff.platform_user_id)
    response = client.post("/api/auth/sso/exchange", json={"ticket": "valid"})
    assert response.status_code == 204
    assert response.cookies["sift_os_session"]
    assert "HttpOnly" in response.headers["set-cookie"]


@pytest.mark.integration
def test_non_staff_platform_user_is_forbidden(client, platform_stub, alice_platform_id) -> None:
    platform_stub.exchange(ticket="valid", audience="sift-os", subject=alice_platform_id)
    assert client.post("/api/auth/sso/exchange", json={"ticket": "valid"}).status_code == 403


@pytest.mark.integration
def test_replayed_assertion_jti_is_rejected(client, platform_stub, active_staff) -> None:
    platform_stub.exchange(ticket="one", audience="sift-os", subject=active_staff.platform_user_id, jti="same")
    assert client.post("/api/auth/sso/exchange", json={"ticket": "one"}).status_code == 204
    platform_stub.exchange(ticket="two", audience="sift-os", subject=active_staff.platform_user_id, jti="same")
    assert client.post("/api/auth/sso/exchange", json={"ticket": "two"}).status_code == 401
```

- [ ] **Step 2: Verify the SSO tests fail**

Run: `.venv/bin/pytest apps/api/tests/auth/test_sso.py apps/api/tests/auth/test_sessions.py -v`

Expected: FAIL because auth routes and verification do not exist.

- [ ] **Step 3: Implement Platform exchange and strict assertion verification**

```python
async def exchange_platform_ticket(ticket: str, settings: Settings) -> str:
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            f"{str(settings.sift_platform_public_url).rstrip('/')}/api/v1/sso/exchange",
            json={"ticket": ticket, "audience": settings.sift_platform_sso_audience},
        )
    if response.status_code != 200:
        raise AuthFailure("SSO_TICKET_INVALID")
    return PlatformExchange.model_validate(response.json()).access_token


def verify_platform_assertion(token: str, jwks: PyJWKClient, settings: Settings) -> PlatformClaims:
    signing_key = jwks.get_signing_key_from_jwt(token)
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.sift_platform_sso_audience,
        issuer=str(settings.sift_platform_sso_issuer).rstrip("/"),
        options={"require": ["iss", "aud", "sub", "exp", "iat", "jti", "product_id", "entitlement_id"]},
    )
    return PlatformClaims.model_validate(payload)
```

`create_local_session()` looks up `StaffMember.platform_user_id == UUID(claims.sub)` and `active IS TRUE`, locks the staff row, inserts the unique assertion JTI and token digest, then returns raw session and CSRF values only to the cookie writer. Duplicate JTI maps to `401 ASSERTION_REPLAYED`; absent/inactive staff maps to `403 STAFF_ACCESS_DENIED`.

- [ ] **Step 4: Implement cookie and CSRF lifecycle**

```python
response.set_cookie(settings.session_cookie_name, raw_session, httponly=True, secure=settings.cookie_secure, samesite="lax", max_age=settings.session_ttl_seconds, path="/")
response.set_cookie(settings.csrf_cookie_name, raw_csrf, httponly=False, secure=settings.cookie_secure, samesite="lax", max_age=settings.session_ttl_seconds, path="/")
```

Logout requires matching CSRF cookie/header, revokes the current session, clears both cookies, and records `auth.logout`. Auth errors never include token, ticket, or claim contents.

- [ ] **Step 5: Run SSO and session tests**

Run: `.venv/bin/pytest apps/api/tests/auth/test_sso.py apps/api/tests/auth/test_sessions.py -v`

Expected: valid staff PASS; non-staff, invalid issuer/audience/signature, expired token, reused ticket/JTI, inactive staff, missing CSRF, and logout tests PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/auth apps/api/tests/auth
git commit -m "feat(auth): integrate SIFT Platform SSO"
```

### Task 5: RBAC policy, `/api/me`, staff seed, and admin controls

**Files:**
- Create: `apps/api/app/staff/permissions.py`
- Create: `apps/api/app/staff/dependencies.py`
- Create: `apps/api/app/staff/schemas.py`
- Create: `apps/api/app/staff/service.py`
- Create: `apps/api/app/staff/routes.py`
- Create: `apps/api/app/staff/seed.py`
- Create: `apps/api/app/db/cli.py`
- Test: `apps/api/tests/staff/test_permissions.py`
- Test: `apps/api/tests/api/test_me.py`
- Test: `apps/api/tests/api/test_staff_admin.py`

**Interfaces:**
- Consumes: current `UserSession` and `StaffMember` models.
- Produces: `CurrentStaff`, `require_permission(Permission)`, `GET /api/me`, `GET /api/staff`, `PATCH /api/staff/{id}/roles`, and idempotent `seed_staff()`.

- [ ] **Step 1: Write the failing permission matrix tests**

```python
@pytest.mark.parametrize(("role", "permission", "allowed"), [
    (StaffRole.ADMIN, Permission.FINANCE_READ, True),
    (StaffRole.SALES_LEAD, Permission.SALES_ASSIGN, True),
    (StaffRole.SALES, Permission.SALES_ASSIGN, False),
    (StaffRole.CODING, Permission.PRODUCT_READ, True),
    (StaffRole.CODING, Permission.FINANCE_READ, False),
])
def test_permission_matrix(role, permission, allowed) -> None:
    assert has_permission({role}, permission) is allowed
```

```python
def test_customer_cannot_use_me(client, customer_session_cookie) -> None:
    assert client.get("/api/me", cookies=customer_session_cookie).status_code == 403
```

- [ ] **Step 2: Verify permission tests fail**

Run: `.venv/bin/pytest apps/api/tests/staff/test_permissions.py apps/api/tests/api/test_me.py apps/api/tests/api/test_staff_admin.py -v`

Expected: FAIL because the policy and routes do not exist.

- [ ] **Step 3: Implement roles and permissions as a closed matrix**

```python
ROLE_PERMISSIONS: Mapping[StaffRole, frozenset[Permission]] = {
    StaffRole.CEO: frozenset(Permission),
    StaffRole.ADMIN: frozenset(Permission),
    StaffRole.SALES_LEAD: frozenset({Permission.DASHBOARD_SALES, Permission.SALES_READ_ALL, Permission.SALES_WRITE_ALL, Permission.SALES_ASSIGN, Permission.PARTNER_READ, Permission.PARTNER_WRITE, Permission.TASK_READ, Permission.TASK_WRITE}),
    StaffRole.SALES: frozenset({Permission.DASHBOARD_SALES, Permission.SALES_READ_OWN, Permission.SALES_WRITE_OWN, Permission.PARTNER_READ_ASSIGNED, Permission.TASK_READ, Permission.TASK_WRITE_OWN}),
    StaffRole.CODING: frozenset({Permission.DASHBOARD_COMPANY, Permission.PRODUCT_READ, Permission.TASK_READ, Permission.TASK_WRITE, Permission.OBJECTIVE_READ}),
}


def require_permission(permission: Permission) -> Callable[..., StaffContext]:
    def dependency(current: CurrentStaff) -> StaffContext:
        if permission not in current.permissions:
            raise ApiError(403, "PERMISSION_DENIED", "Non hai i permessi necessari.")
        return current
    return dependency
```

`CurrentStaff` authenticates the opaque session, rejects expired/revoked sessions and inactive staff, loads all roles in one query, and exposes a frozen permission set. Admin role changes use a transaction, prevent removal of the last active CEO/Admin, and record previous/new roles in audit.

- [ ] **Step 4: Add the exact idempotent staff seed**

```python
STAFF_SEED = (
    StaffSeed(UUID("4ac5662a-1eaa-4f47-9dae-406eefdf6e40"), "Alessandro Bellucco", Department.CODING, {StaffRole.CEO, StaffRole.ADMIN, StaffRole.CODING}),
    StaffSeed(UUID("0de642b4-8a97-422b-8aaa-e05d581e528a"), "Lorenzo Di Lenna", Department.SALES, {StaffRole.SALES_LEAD}),
    StaffSeed(UUID("6cf7bdfc-c119-454b-ab3d-c448e56ed197"), "Alexis Solomon", Department.SALES, {StaffRole.SALES}),
    StaffSeed(UUID("a02ba528-67bf-405b-8d81-bafb3d5314f7"), "Braghin Gregorio", Department.SALES, {StaffRole.SALES}),
    StaffSeed(UUID("8e195348-3a4a-479a-af5b-3cf4cc69ae3e"), "Melchionda Federico", Department.SALES, {StaffRole.SALES}),
    StaffSeed(UUID("d13cd18f-bd38-4ebc-b379-4a8fc39408f0"), "Michael Nordin", Department.CODING, {StaffRole.CODING}),
    StaffSeed(UUID("da0a87e1-ded0-449b-9988-6e4e8f825ed4"), "Dalsoglio Luca", Department.CODING, {StaffRole.CODING}),
    StaffSeed(UUID("2011db5d-7c26-4a1e-aa60-9007f9dc8a87"), "Matteo Pinton", Department.CODING, {StaffRole.CODING}),
)
```

The seed updates canonical display names and required initial roles without reactivating a deliberately deactivated staff record or deleting later admin-added roles. No ninth record is created.

- [ ] **Step 5: Verify RBAC, staff endpoints, and seed idempotency**

Run: `.venv/bin/pytest apps/api/tests/staff apps/api/tests/api/test_me.py apps/api/tests/api/test_staff_admin.py -v`

Expected: all matrix, inactive staff, coder Finance denial, Sales Lead assignment, admin audit, and two-pass seed tests PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/staff apps/api/app/db/cli.py apps/api/tests
git commit -m "feat(rbac): add staff mapping and permissions"
```

### Task 6: Minimal SIFT Platform internal-product integration

**Files (in `/Users/sir/Desktop/empty/sift-platform`):**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/products/models.py`
- Modify: `backend/app/products/seed.py`
- Modify: `backend/app/entitlements/policy.py`
- Create: `backend/migrations/versions/20260908_0003_internal_products.py`
- Modify: `frontend/src/pages/HomePage.tsx`
- Modify: `frontend/src/styles/global.css`
- Modify: `.env.example`
- Test: `backend/tests/products/test_internal_product.py`
- Test: `backend/tests/sso/test_os_access.py`
- Test: `frontend/src/pages/HomePage.test.tsx`

**Interfaces:**
- Consumes: existing Platform product catalog, entitlement checks, one-time SSO tickets, RS256 exchange, and the approved local HEAD.
- Produces: product key/audience `sift-os`, `SIFT_OS_LAUNCH_URL`, and backend-filtered internal visibility.

- [ ] **Step 1: Create a dedicated Platform branch and write failing visibility tests**

Run: `git switch -c codex/sift-os-integration`

```python
def test_internal_product_is_hidden_without_explicit_entitlement(client, alice_auth) -> None:
    response = client.get(f"/api/v1/workspaces/{alice_auth.workspace_id}/products", cookies=alice_auth.cookies)
    assert "sift-os" not in {item["key"] for item in response.json()["items"]}


def test_internal_staff_can_authorize_os_ticket(client, alessandro_auth, os_entitlement) -> None:
    response = client.post("/api/v1/sso/authorize", json={"workspace_id": str(alessandro_auth.workspace_id), "product_id": str(os_entitlement.product_id)}, headers=alessandro_auth.csrf_headers, cookies=alessandro_auth.cookies)
    assert response.status_code == 200
    assert response.json()["redirect_url"].startswith("https://os.example/")
```

- [ ] **Step 2: Verify tests fail before modifying Platform behavior**

Run: `.venv/bin/pytest backend/tests/products/test_internal_product.py backend/tests/sso/test_os_access.py -v`

Expected: FAIL because internal products and SIFT OS seed do not exist.

- [ ] **Step 3: Add explicit product visibility and SIFT OS configuration**

```python
class Product(...):
    visibility: Mapped[ProductVisibility] = mapped_column(
        enum_type(ProductVisibility, "product_visibility"),
        default=ProductVisibility.CUSTOMER,
        nullable=False,
    )
```

```python
"sift-os": ProductDefinition(
    name="SIFT OS",
    short_description="Controllo operativo interno di SIFT.",
    long_description="CRM, partner, prodotto, attività e metriche aziendali in un unico sistema operativo.",
    icon="operations",
    preview_image="",
    display_order=90,
    launch_url_setting="sift_os_launch_url",
    visibility=ProductVisibility.INTERNAL,
)
```

The product-list query includes customer products as before but includes an internal product only when the current user has an active direct entitlement for that product. Authorization still rechecks the entitlement server-side. Add `SIFT_OS_LAUNCH_URL=` to `.env.example`; do not hardcode a domain.

- [ ] **Step 4: Add the Platform UI row without exposing it to customers**

`ProductMark` receives an `operations` mark built from the existing icon treatment; the row uses the current product layout and `launchProduct()` flow. No frontend staff/email check is added because the API already filters the catalog.

- [ ] **Step 5: Run the complete affected Platform checks**

Run: `.venv/bin/ruff check backend && .venv/bin/mypy backend/app && .venv/bin/pytest && npm --prefix frontend run lint && npm --prefix frontend run typecheck && npm --prefix frontend test -- --run && npm --prefix frontend run build`

Expected: all existing and new Platform checks PASS; customer fixture does not receive SIFT OS; staff fixture launches with `aud=sift-os`.

- [ ] **Step 6: Commit Platform integration**

```bash
git add backend frontend .env.example
git commit -m "feat(platform): add gated SIFT OS access"
```

### Task 7: Role-aware web shell and SSO callback

**Files:**
- Create: `apps/web/src/app/queryClient.ts`
- Create: `apps/web/src/app/router.tsx`
- Create: `apps/web/src/app/App.tsx`
- Create: `apps/web/src/features/auth/types.ts`
- Create: `apps/web/src/features/auth/api.ts`
- Create: `apps/web/src/features/auth/AuthProvider.tsx`
- Create: `apps/web/src/features/auth/guards.tsx`
- Create: `apps/web/src/components/Brand.tsx`
- Create: `apps/web/src/components/AppShell.tsx`
- Create: `apps/web/src/pages/SsoCallbackPage.tsx`
- Create: `apps/web/src/pages/AccessDeniedPage.tsx`
- Create: `apps/web/src/pages/DashboardPage.tsx`
- Create: `apps/web/src/styles/tokens.css`
- Create: `apps/web/src/styles/global.css`
- Test: `apps/web/src/features/auth/AuthProvider.test.tsx`
- Test: `apps/web/src/components/AppShell.test.tsx`
- Test: `apps/web/src/pages/SsoCallbackPage.test.tsx`

**Interfaces:**
- Consumes: `POST /api/auth/sso/exchange`, `GET /api/me`, `POST /api/logout`, and `MeResponse.permissions`.
- Produces: protected routes, role-specific landing, role-filtered navigation, and same-origin authenticated requests.

- [ ] **Step 1: Write failing callback and navigation tests**

```tsx
it("exchanges the ticket without storing it and removes it from the URL", async () => {
  window.history.replaceState({}, "", "/auth/callback?sso_ticket=secret&sso_audience=sift-os");
  render(<SsoCallbackPage />);
  await waitFor(() => expect(exchangeSso).toHaveBeenCalledWith("secret"));
  expect(window.localStorage).toHaveLength(0);
  expect(window.location.search).toBe("");
});


it("does not render Finance for coding-only staff", async () => {
  renderShell(me({roles:["CODING"], permissions:["product:read"]}));
  expect(screen.getByRole("link", {name:"Product Operations"})).toBeVisible();
  expect(screen.queryByRole("link", {name:"Finance"})).toBeNull();
});
```

- [ ] **Step 2: Verify frontend tests fail**

Run: `npm --prefix apps/web test -- --run src/features/auth/AuthProvider.test.tsx src/components/AppShell.test.tsx src/pages/SsoCallbackPage.test.tsx`

Expected: FAIL because the app shell and auth flow do not exist.

- [ ] **Step 3: Implement the safe HTTP client and auth provider**

```ts
export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const csrf = document.cookie.split("; ").find(v => v.startsWith("sift_os_csrf="))?.split("=")[1];
  if (csrf && !["GET", "HEAD", "OPTIONS"].includes(init.method ?? "GET")) headers.set("X-CSRF-Token", decodeURIComponent(csrf));
  const response = await fetch(`/api${path}`, {...init, headers, credentials:"include"});
  if (!response.ok) throw await ApiClientError.fromResponse(response);
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}
```

`AuthProvider` loads `/me`, exposes `loading | authenticated | anonymous | forbidden`, retries only network errors, and clears cached private queries on logout. `SsoCallbackPage` extracts and immediately removes the query string, validates `sso_audience === "sift-os"`, performs the exchange, then navigates to `/`.

- [ ] **Step 4: Implement the role-aware shell and initial dashboards**

Navigation items declare a required permission and are filtered from `/me`. Route guards repeat the UI permission check for usability while the API remains authoritative. `/` routes CEO/Admin to a cockpit placeholder backed only by authenticated identity, Sales Lead to Sales, Sales to My Day, and Coding to Product Operations. These pages contain no fake business metrics; they show explicit empty/foundation states until later vertical plans add real endpoints.

Copy Platform design tokens into semantic CSS variables after comparing the current `frontend/src/styles/global.css`; recreate the SIFT wordmark as a reusable component, preserve focus-visible states, and use no model-authored decorative SVG illustration.

- [ ] **Step 5: Run frontend tests and build**

Run: `npm --prefix apps/web run lint && npm --prefix apps/web run typecheck && npm --prefix apps/web test -- --run && npm --prefix apps/web run build`

Expected: all checks PASS; unauthorized, forbidden, loading, empty, network, and logout states render without a blank screen.

- [ ] **Step 6: Commit**

```bash
git add apps/web
git commit -m "feat(web): add SSO shell and role navigation"
```

### Task 8: Docker, local PostgreSQL, CI, and operational documentation

**Files:**
- Create: `Dockerfile.api`
- Create: `Dockerfile.web`
- Create: `deploy/api-start.sh`
- Create: `deploy/web-nginx.conf`
- Create: `docker-compose.yml`
- Create: `.github/workflows/ci.yml`
- Create: `README.md`
- Create: `docs/ARCHITECTURE.md`
- Create: `docs/AUTH_ARCHITECTURE.md`
- Create: `docs/RBAC.md`
- Create: `docs/DATABASE.md`
- Create: `docs/API.md`
- Create: `docs/DEPLOYMENT.md`
- Create: `docs/OPERATIONS.md`
- Create: `docs/SECURITY.md`
- Test: `apps/api/tests/security/test_no_secrets.py`

**Interfaces:**
- Consumes: all foundation runtime and test commands.
- Produces: reproducible local startup, separate Railway images, CI gates, and exact operator/developer instructions.

- [ ] **Step 1: Write the failing repository-safety test**

```python
def test_tracked_files_contain_no_private_key_or_live_secret() -> None:
    tracked = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
    forbidden = ("BEGIN PRIVATE KEY", "gho_", "postgresql://postgres:")
    offenders = [path for path in tracked if Path(path).is_file() and any(token in Path(path).read_text(errors="ignore") for token in forbidden)]
    assert offenders == []
```

- [ ] **Step 2: Verify the safety test and Docker targets are initially absent**

Run: `.venv/bin/pytest apps/api/tests/security/test_no_secrets.py -v && test -f Dockerfile.api && test -f Dockerfile.web`

Expected: safety test PASS and file checks FAIL because Dockerfiles are absent.

- [ ] **Step 3: Add deterministic containers and local orchestration**

```dockerfile
# Dockerfile.api
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml ./
COPY apps/api/app ./apps/api/app
RUN python -m pip wheel --no-cache-dir --wheel-dir /wheels .
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
RUN groupadd --gid 10001 sift && useradd --uid 10001 --gid 10001 --no-create-home sift
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels sift-os-api && rm -rf /wheels
COPY apps/api/alembic.ini ./apps/api/alembic.ini
COPY apps/api/migrations ./apps/api/migrations
COPY deploy/api-start.sh ./deploy/api-start.sh
USER 10001
ENTRYPOINT ["/app/deploy/api-start.sh"]
```

`Dockerfile.web` builds `apps/web` from the root lockfile and serves static assets with unprivileged nginx. `deploy/web-nginx.conf` proxies `/api/` to `${SIFT_OS_API_ORIGIN}` through an environment-rendered template and serves `index.html` for SPA routes. `docker-compose.yml` defines `postgres:17-alpine`, an isolated healthcheck, API, and web; development database and test database are separate.

- [ ] **Step 4: Add CI gates**

```yaml
jobs:
  backend:
    services:
      postgres:
        image: postgres:17-alpine
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12", cache: pip}
      - run: pip install -e '.[dev]'
      - run: ruff check apps/api && ruff format --check apps/api && mypy apps/api/app
      - run: alembic -c apps/api/alembic.ini upgrade head && pytest
  frontend:
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: {node-version: "24", cache: npm}
      - run: npm ci
      - run: npm --prefix apps/web run lint && npm --prefix apps/web run typecheck && npm --prefix apps/web test -- --run && npm --prefix apps/web run build
  containers:
    steps:
      - uses: actions/checkout@v4
      - run: docker build -f Dockerfile.api -t sift-os-api:test .
      - run: docker build -f Dockerfile.web -t sift-os-web:test .
```

- [ ] **Step 5: Write exact documentation**

`README.md` covers clone, `.env`, PostgreSQL, Alembic, API, web, tests, and Docker. `AUTH_ARCHITECTURE.md` records the discovered opaque Platform session and chosen ticket → exchange → RS256 → local session flow. `RBAC.md` contains the complete role/permission matrix. `DEPLOYMENT.md` defines `sift-os-web`, `sift-os-api`, private PostgreSQL, staging, production, build/start/healthcheck, variables without values, migration sequencing, smoke tests, custom-domain placeholder policy, and rollback. `SECURITY.md` documents trust boundaries, threat controls, secret rotation, CSRF, CORS, logging exclusions, and incident steps.

- [ ] **Step 6: Run the phase acceptance suite**

Run: `.venv/bin/ruff check apps/api && .venv/bin/ruff format --check apps/api && .venv/bin/mypy apps/api/app && TEST_DATABASE_URL=postgresql+psycopg://sift_os:sift_os@localhost:5433/sift_os_test .venv/bin/pytest && npm --prefix apps/web run lint && npm --prefix apps/web run typecheck && npm --prefix apps/web test -- --run && npm --prefix apps/web run build && docker build -f Dockerfile.api -t sift-os-api:test . && docker build -f Dockerfile.web -t sift-os-web:test .`

Expected: every command exits 0; all tests PASS; both images build; no secret scan offenders exist.

- [ ] **Step 7: Commit the operational foundation**

```bash
git add Dockerfile.api Dockerfile.web deploy docker-compose.yml .github README.md docs apps/api/tests/security
git commit -m "chore: add CI containers and operations docs"
```

## Phase acceptance gate

Before starting the CRM plan, verify all of the following with recorded command output:

- Platform staff can launch SIFT OS without a second login.
- All eight verified Platform UUIDs map to the intended roles.
- `Aliceg76`, an unmapped Platform customer, and a direct anonymous request are rejected.
- Coding cannot access Finance; Sales cannot assign or mutate another owner's records; Sales Lead and CEO permissions match the matrix.
- Platform and OS test suites pass independently.
- SIFT OS frontend and both Docker images build.
- Alembic upgrades a blank PostgreSQL database and can downgrade/upgrade the foundation revision.
- No secrets are tracked, logged, or returned in API errors.
- The implementation is documented without claiming staging or production deployment until those environments have actually passed smoke tests.
