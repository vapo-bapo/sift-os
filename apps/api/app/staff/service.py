from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import AuditResult
from app.audit.service import record_audit_log
from app.core.errors import ApiError
from app.staff.dependencies import CurrentStaff
from app.staff.models import StaffMember, StaffMemberRole
from app.staff.permissions import Permission, permissions_for_roles
from app.staff.roles import StaffRole
from app.staff.schemas import MeResponse, StaffResponse


def _ordered_roles(roles: Iterable[StaffRole]) -> list[StaffRole]:
    return sorted(roles, key=lambda role: role.value)


def _ordered_permissions(roles: Iterable[StaffRole]) -> list[Permission]:
    return sorted(permissions_for_roles(roles), key=lambda permission: permission.value)


def me_response(current: CurrentStaff) -> MeResponse:
    return MeResponse(
        id=current.staff.id,
        display_name=current.staff.display_name,
        department=current.staff.department,
        roles=_ordered_roles(current.roles),
        permissions=_ordered_permissions(current.roles),
    )


def staff_response(staff: StaffMember, roles: Iterable[StaffRole]) -> StaffResponse:
    ordered_roles = _ordered_roles(roles)
    return StaffResponse(
        id=staff.id,
        display_name=staff.display_name,
        department=staff.department,
        active=staff.active,
        roles=ordered_roles,
        permissions=_ordered_permissions(ordered_roles),
    )


def list_staff(db: Session) -> list[StaffResponse]:
    rows = db.execute(
        select(StaffMember, StaffMemberRole.role)
        .outerjoin(StaffMemberRole, StaffMemberRole.staff_member_id == StaffMember.id)
        .order_by(StaffMember.display_name, StaffMember.id)
    ).all()
    staff_by_id: dict[UUID, StaffMember] = {}
    roles_by_staff: dict[UUID, set[StaffRole]] = defaultdict(set)
    for staff, role in rows:
        staff_by_id[staff.id] = staff
        if role is not None:
            roles_by_staff[staff.id].add(role)
    return [
        staff_response(staff, roles_by_staff[staff_id]) for staff_id, staff in staff_by_id.items()
    ]


def _ensure_not_last_privileged_role(
    db: Session, *, staff_id: UUID, previous_roles: set[StaffRole], new_roles: set[StaffRole]
) -> None:
    for role in (StaffRole.CEO, StaffRole.ADMIN):
        if role not in previous_roles or role in new_roles:
            continue
        active_ids = set(
            db.scalars(
                select(StaffMember.id)
                .join(StaffMemberRole, StaffMemberRole.staff_member_id == StaffMember.id)
                .where(StaffMember.active.is_(True), StaffMemberRole.role == role)
                .with_for_update()
            )
        )
        if active_ids == {staff_id}:
            raise ApiError(
                status_code=409,
                code="LAST_PRIVILEGED_ROLE",
                message="Non puoi rimuovere l'ultimo ruolo privilegiato attivo.",
            )


def update_staff_roles(
    db: Session,
    *,
    actor: CurrentStaff,
    staff_id: UUID,
    roles: set[StaffRole],
    request_id: str,
    ip_address: str | None,
    user_agent_summary: str | None,
) -> StaffResponse:
    staff = db.scalar(select(StaffMember).where(StaffMember.id == staff_id).with_for_update())
    if staff is None:
        raise ApiError(
            status_code=404,
            code="STAFF_NOT_FOUND",
            message="Membro dello staff non trovato.",
        )
    role_records = list(
        db.scalars(
            select(StaffMemberRole)
            .where(StaffMemberRole.staff_member_id == staff_id)
            .with_for_update()
        )
    )
    previous_roles = {record.role for record in role_records}
    _ensure_not_last_privileged_role(
        db, staff_id=staff_id, previous_roles=previous_roles, new_roles=roles
    )

    for record in role_records:
        db.delete(record)
    db.flush()
    db.add_all(StaffMemberRole(staff_member_id=staff.id, role=role) for role in roles)
    db.flush()
    record_audit_log(
        db,
        actor_staff_id=actor.staff.id,
        action="staff.roles.updated",
        entity_type="staff_member",
        entity_id=staff.id,
        previous={"roles": [role.value for role in _ordered_roles(previous_roles)]},
        new={"roles": [role.value for role in _ordered_roles(roles)]},
        request_id=request_id,
        ip_address=ip_address,
        user_agent_summary=user_agent_summary,
        result=AuditResult.SUCCESS,
    )
    return staff_response(staff, roles)
