from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    Base,
    CreatedAtMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    enum_type,
)
from app.staff.roles import Department, StaffRole


class StaffMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "staff_members"

    platform_user_id: Mapped[UUID] = mapped_column(Uuid, unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(201), nullable=False)
    department: Mapped[Department] = mapped_column(
        enum_type(Department, "department"), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class StaffMemberRole(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "staff_member_roles"
    __table_args__ = (UniqueConstraint("staff_member_id", "role", name="uq_staff_role"),)

    staff_member_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff_members.id", ondelete="CASCADE")
    )
    role: Mapped[StaffRole] = mapped_column(enum_type(StaffRole, "staff_role"), nullable=False)
