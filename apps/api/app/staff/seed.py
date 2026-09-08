from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.staff.models import StaffMember, StaffMemberRole
from app.staff.roles import Department, StaffRole


@dataclass(frozen=True, slots=True)
class StaffSeed:
    platform_user_id: UUID
    display_name: str
    department: Department
    roles: frozenset[StaffRole]


STAFF_SEED = (
    StaffSeed(
        UUID("4ac5662a-1eaa-4f47-9dae-406eefdf6e40"),
        "Alessandro Bellucco",
        Department.CODING,
        frozenset({StaffRole.CEO, StaffRole.ADMIN, StaffRole.CODING}),
    ),
    StaffSeed(
        UUID("0de642b4-8a97-422b-8aaa-e05d581e528a"),
        "Lorenzo Di Lenna",
        Department.SALES,
        frozenset({StaffRole.SALES_LEAD}),
    ),
    StaffSeed(
        UUID("6cf7bdfc-c119-454b-ab3d-c448e56ed197"),
        "Alexis Solomon",
        Department.SALES,
        frozenset({StaffRole.SALES}),
    ),
    StaffSeed(
        UUID("a02ba528-67bf-405b-8d81-bafb3d5314f7"),
        "Braghin Gregorio",
        Department.SALES,
        frozenset({StaffRole.SALES}),
    ),
    StaffSeed(
        UUID("8e195348-3a4a-479a-af5b-3cf4cc69ae3e"),
        "Melchionda Federico",
        Department.SALES,
        frozenset({StaffRole.SALES}),
    ),
    StaffSeed(
        UUID("d13cd18f-bd38-4ebc-b379-4a8fc39408f0"),
        "Michael Nordin",
        Department.CODING,
        frozenset({StaffRole.CODING}),
    ),
    StaffSeed(
        UUID("da0a87e1-ded0-449b-9988-6e4e8f825ed4"),
        "Dalsoglio Luca",
        Department.CODING,
        frozenset({StaffRole.CODING}),
    ),
    StaffSeed(
        UUID("2011db5d-7c26-4a1e-aa60-9007f9dc8a87"),
        "Matteo Pinton",
        Department.CODING,
        frozenset({StaffRole.CODING}),
    ),
)


def seed_staff(db: Session) -> None:
    for entry in STAFF_SEED:
        staff = db.scalar(
            select(StaffMember).where(StaffMember.platform_user_id == entry.platform_user_id)
        )
        if staff is None:
            staff = StaffMember(
                platform_user_id=entry.platform_user_id,
                display_name=entry.display_name,
                department=entry.department,
            )
            db.add(staff)
            db.flush()
        else:
            staff.display_name = entry.display_name
            staff.department = entry.department

        existing_roles = set(
            db.scalars(
                select(StaffMemberRole.role).where(StaffMemberRole.staff_member_id == staff.id)
            )
        )
        db.add_all(
            StaffMemberRole(staff_member_id=staff.id, role=role)
            for role in entry.roles - existing_roles
        )
    db.flush()
