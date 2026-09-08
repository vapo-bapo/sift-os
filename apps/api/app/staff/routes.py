from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.staff.dependencies import CurrentStaff, get_current_staff, require_csrf, require_permission
from app.staff.permissions import Permission
from app.staff.schemas import MeResponse, StaffResponse, StaffRolesUpdateRequest
from app.staff.service import list_staff, me_response, update_staff_roles

router = APIRouter(prefix="/api", tags=["staff"])

AdminStaff = Annotated[CurrentStaff, Depends(require_permission(Permission.STAFF_MANAGE))]


@router.get("/me", response_model=MeResponse)
def me(current: Annotated[CurrentStaff, Depends(get_current_staff)]) -> MeResponse:
    return me_response(current)


@router.get("/staff", response_model=list[StaffResponse])
def staff_directory(
    db: Annotated[Session, Depends(get_db)], current: AdminStaff
) -> list[StaffResponse]:
    del current
    return list_staff(db)


@router.patch("/staff/{staff_id}/roles", response_model=StaffResponse)
def change_staff_roles(
    staff_id: UUID,
    payload: StaffRolesUpdateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current: AdminStaff,
    csrf_current: Annotated[CurrentStaff, Depends(require_csrf)],
) -> StaffResponse:
    del csrf_current
    result = update_staff_roles(
        db,
        actor=current,
        staff_id=staff_id,
        roles=payload.roles,
        request_id=request.state.request_id,
        ip_address=request.client.host if request.client is not None else None,
        user_agent_summary=request.headers.get("user-agent", "")[:256] or None,
    )
    db.commit()
    return result
