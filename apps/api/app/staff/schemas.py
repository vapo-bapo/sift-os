from uuid import UUID

from pydantic import BaseModel

from app.staff.permissions import Permission
from app.staff.roles import Department, StaffRole


class MeResponse(BaseModel):
    id: UUID
    display_name: str
    department: Department
    roles: list[StaffRole]
    permissions: list[Permission]


class StaffResponse(MeResponse):
    active: bool


class StaffRolesUpdateRequest(BaseModel):
    roles: set[StaffRole]
