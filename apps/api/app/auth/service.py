from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.csrf import csrf_values_match
from app.auth.models import UserSession
from app.auth.schemas import PlatformClaims
from app.auth.sso import AuthFailure
from app.auth.tokens import new_opaque_token, token_digest
from app.core.config import Settings
from app.staff.models import StaffMember


@dataclass(frozen=True, slots=True)
class LocalSession:
    session: UserSession
    raw_session: str
    raw_csrf: str


def validate_local_session_csrf(
    session: UserSession,
    *,
    csrf_cookie: str | None,
    csrf_header: str | None,
    settings: Settings,
) -> None:
    if (
        csrf_cookie is None
        or csrf_header is None
        or not csrf_values_match(csrf_cookie, csrf_header)
    ):
        raise AuthFailure("CSRF_INVALID", status_code=403)
    expected_csrf = token_digest(csrf_cookie, settings.csrf_secret)
    if not secrets.compare_digest(session.csrf_nonce_digest, expected_csrf):
        raise AuthFailure("CSRF_INVALID", status_code=403)


def create_local_session(
    db: Session,
    *,
    claims: PlatformClaims,
    settings: Settings,
    now: datetime | None = None,
) -> LocalSession:
    created_at = now or datetime.now(UTC)
    staff = db.scalar(
        select(StaffMember)
        .where(
            StaffMember.platform_user_id == claims.sub,
            StaffMember.active.is_(True),
        )
        .with_for_update()
    )
    if staff is None:
        raise AuthFailure("STAFF_ACCESS_DENIED", status_code=403)

    replayed = db.scalar(
        select(UserSession.id).where(UserSession.platform_assertion_jti == claims.jti)
    )
    if replayed is not None:
        raise AuthFailure("ASSERTION_REPLAYED")

    raw_session = new_opaque_token()
    raw_csrf = new_opaque_token()
    user_session = UserSession(
        staff_member_id=staff.id,
        token_digest=token_digest(raw_session, settings.session_secret),
        csrf_nonce_digest=token_digest(raw_csrf, settings.csrf_secret),
        platform_assertion_jti=claims.jti,
        expires_at=created_at + timedelta(seconds=settings.session_ttl_seconds),
    )
    try:
        with db.begin_nested():
            db.add(user_session)
            db.flush()
    except IntegrityError:
        raise AuthFailure("ASSERTION_REPLAYED") from None
    return LocalSession(user_session, raw_session, raw_csrf)


def revoke_local_session(
    db: Session,
    *,
    raw_session: str | None,
    csrf_cookie: str | None,
    csrf_header: str | None,
    settings: Settings,
    now: datetime | None = None,
) -> UserSession:
    if raw_session is None:
        raise AuthFailure("SESSION_INVALID")

    revoked_at = now or datetime.now(UTC)
    user_session = db.scalar(
        select(UserSession)
        .where(UserSession.token_digest == token_digest(raw_session, settings.session_secret))
        .with_for_update()
    )
    if (
        user_session is None
        or user_session.revoked_at is not None
        or user_session.expires_at <= revoked_at
    ):
        raise AuthFailure("SESSION_INVALID")
    validate_local_session_csrf(
        user_session,
        csrf_cookie=csrf_cookie,
        csrf_header=csrf_header,
        settings=settings,
    )

    user_session.revoked_at = revoked_at
    db.flush()
    return user_session
