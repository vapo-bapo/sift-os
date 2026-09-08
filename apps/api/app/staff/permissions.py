from collections.abc import Iterable, Mapping
from enum import StrEnum

from app.staff.roles import StaffRole


class Permission(StrEnum):
    DASHBOARD_SALES = "dashboard:sales"
    DASHBOARD_COMPANY = "dashboard:company"
    SALES_READ_ALL = "sales:read_all"
    SALES_WRITE_ALL = "sales:write_all"
    SALES_ASSIGN = "sales:assign"
    SALES_READ_OWN = "sales:read_own"
    SALES_WRITE_OWN = "sales:write_own"
    PARTNER_READ = "partner:read"
    PARTNER_WRITE = "partner:write"
    PARTNER_READ_ASSIGNED = "partner:read_assigned"
    TASK_READ = "task:read"
    TASK_WRITE = "task:write"
    TASK_WRITE_OWN = "task:write_own"
    PRODUCT_READ = "product:read"
    OBJECTIVE_READ = "objective:read"
    FINANCE_READ = "finance:read"
    STAFF_MANAGE = "staff:manage"


ROLE_PERMISSIONS: Mapping[StaffRole, frozenset[Permission]] = {
    StaffRole.CEO: frozenset(Permission),
    StaffRole.ADMIN: frozenset(Permission),
    StaffRole.SALES_LEAD: frozenset(
        {
            Permission.DASHBOARD_SALES,
            Permission.SALES_READ_ALL,
            Permission.SALES_WRITE_ALL,
            Permission.SALES_ASSIGN,
            Permission.PARTNER_READ,
            Permission.PARTNER_WRITE,
            Permission.TASK_READ,
            Permission.TASK_WRITE,
        }
    ),
    StaffRole.SALES: frozenset(
        {
            Permission.DASHBOARD_SALES,
            Permission.SALES_READ_OWN,
            Permission.SALES_WRITE_OWN,
            Permission.PARTNER_READ_ASSIGNED,
            Permission.TASK_READ,
            Permission.TASK_WRITE_OWN,
        }
    ),
    StaffRole.CODING: frozenset(
        {
            Permission.DASHBOARD_COMPANY,
            Permission.PRODUCT_READ,
            Permission.TASK_READ,
            Permission.TASK_WRITE,
            Permission.OBJECTIVE_READ,
        }
    ),
}


def permissions_for_roles(roles: Iterable[StaffRole]) -> frozenset[Permission]:
    return frozenset(permission for role in roles for permission in ROLE_PERMISSIONS[role])


def has_permission(roles: Iterable[StaffRole], permission: Permission) -> bool:
    return permission in permissions_for_roles(roles)
