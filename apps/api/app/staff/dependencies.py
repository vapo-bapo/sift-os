from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import UserSession
from app.auth.service import validate_local_session_csrf
from app.auth.tokens import token_digest
from app.core.errors import ApiError
from app.db.session import get_db
from app.staff.models import StaffMember, StaffMemberRole
from app.staff.permissions import Permission, permissions_for_roles
from app.staff.roles import StaffRole


@dataclass(frozen=True, slots=True)
class CurrentStaff:
    session: UserSession
    staff: StaffMember
    roles: frozenset[StaffRole]
    permissions: frozenset[Permission]


def get_current_staff(request: Request, db: Annotated[Session, Depends(get_db)]) -> CurrentStaff:
    settings = request.app.state.settings
    raw_session = request.cookies.get(settings.session_cookie_name)
    if raw_session is None:
        raise ApiError(
            status_code=401,
            code="SESSION_INVALID",
            message="La sessione non è valida o è scaduta.",
        )

    rows = db.execute(
        select(UserSession, StaffMember, StaffMemberRole.role)
        .join(StaffMember, StaffMember.id == UserSession.staff_member_id)
        .outerjoin(StaffMemberRole, StaffMemberRole.staff_member_id == StaffMember.id)
        .where(UserSession.token_digest == token_digest(raw_session, settings.session_secret))
    ).all()
    if not rows:
        raise ApiError(
            status_code=401,
            code="SESSION_INVALID",
            message="La sessione non è valida o è scaduta.",
        )

    session, staff, _ = rows[0]
    if session.revoked_at is not None or session.expires_at <= datetime.now(UTC):
        raise ApiError(
            status_code=401,
            code="SESSION_INVALID",
            message="La sessione non è valida o è scaduta.",
        )
    if not staff.active:
        raise ApiError(
            status_code=403,
            code="STAFF_ACCESS_DENIED",
            message="L'utente non è autorizzato ad accedere a SIFT OS.",
        )

    roles = frozenset(role for _, _, role in rows if role is not None)
    return CurrentStaff(
        session=session,
        staff=staff,
        roles=roles,
        permissions=permissions_for_roles(roles),
    )


def require_permission(permission: Permission) -> Callable[..., CurrentStaff]:
    def dependency(
        current: Annotated[CurrentStaff, Depends(get_current_staff)],
    ) -> CurrentStaff:
        if permission not in current.permissions:
            raise ApiError(
                status_code=403,
                code="PERMISSION_DENIED",
                message="Non hai i permessi necessari.",
            )
        return current

    return dependency


def require_csrf(
    request: Request,
    current: Annotated[CurrentStaff, Depends(get_current_staff)],
) -> CurrentStaff:
    settings = request.app.state.settings
    validate_local_session_csrf(
        current.session,
        csrf_cookie=request.cookies.get(settings.csrf_cookie_name),
        csrf_header=request.headers.get("X-CSRF-Token"),
        settings=settings,
    )
    return current
