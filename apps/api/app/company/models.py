from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin, enum_type


class Workstream(StrEnum):
    SALES = "sales"
    ARGUS = "argus"
    LYNX = "lynx"
    LEGAL = "legal"
    FINANCE = "finance"
    CODING = "coding"
    COMPANY = "company"


class ObjectiveStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    AT_RISK = "at_risk"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskPriority(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class TaskStatus(StrEnum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"


class Objective(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "objectives"
    __table_args__ = (
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_objective_progress"),
    )

    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff_members.id", ondelete="RESTRICT"), index=True
    )
    department: Mapped[Workstream] = mapped_column(enum_type(Workstream, "workstream"), index=True)
    status: Mapped[ObjectiveStatus] = mapped_column(
        enum_type(ObjectiveStatus, "objective_status"), index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    archived_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff_members.id", ondelete="SET NULL")
    )


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tasks"

    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    objective_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("objectives.id", ondelete="SET NULL"), index=True
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff_members.id", ondelete="RESTRICT"), index=True
    )
    department: Mapped[Workstream] = mapped_column(enum_type(Workstream, "workstream"), index=True)
    priority: Mapped[TaskPriority] = mapped_column(
        enum_type(TaskPriority, "task_priority"), index=True
    )
    status: Mapped[TaskStatus] = mapped_column(enum_type(TaskStatus, "task_status"), index=True)
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("staff_members.id", ondelete="RESTRICT"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    archived_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff_members.id", ondelete="SET NULL")
    )


class Notification(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "notifications"

    recipient_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff_members.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[UUID | None] = mapped_column(Uuid)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
