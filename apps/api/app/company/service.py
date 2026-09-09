from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, true
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.company.models import Notification, Objective, Task, TaskStatus
from app.company.schemas import ObjectiveCreate, ObjectivePatch, TaskCreate, TaskPatch
from app.core.errors import ApiError
from app.staff.dependencies import CurrentStaff
from app.staff.permissions import Permission


def completion_timestamp(
    status: TaskStatus, current: datetime | None, now: datetime | None = None
) -> datetime | None:
    if status is TaskStatus.DONE:
        return current or now or datetime.now(UTC)
    return None


def _task_scope(current: CurrentStaff) -> ColumnElement[bool]:
    if (
        Permission.TASK_WRITE_OWN in current.permissions
        and Permission.TASK_WRITE not in current.permissions
    ):
        return Task.owner_id == current.staff.id
    return true()


def list_objectives(db: Session, *, page: int, page_size: int) -> tuple[list[Objective], int]:
    criteria = Objective.archived_at.is_(None)
    total = db.scalar(select(func.count()).select_from(Objective).where(criteria)) or 0
    items = list(
        db.scalars(
            select(Objective)
            .where(criteria)
            .order_by(Objective.due_date.asc().nullslast(), Objective.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, total


def create_objective(db: Session, payload: ObjectiveCreate) -> Objective:
    objective = Objective(**payload.model_dump())
    db.add(objective)
    db.flush()
    return objective


def update_objective(
    db: Session, objective_id: UUID, payload: ObjectivePatch, actor_id: UUID
) -> Objective:
    objective = db.get(Objective, objective_id)
    if objective is None or objective.archived_at is not None:
        raise ApiError(
            status_code=404, code="OBJECTIVE_NOT_FOUND", message="Obiettivo non trovato."
        )
    values = payload.model_dump(exclude_unset=True, exclude={"archive"})
    for key, value in values.items():
        setattr(objective, key, value)
    if payload.archive:
        objective.archived_at = datetime.now(UTC)
        objective.archived_by_id = actor_id
        objective.status = objective.status.ARCHIVED
    db.flush()
    return objective


def list_tasks(
    db: Session,
    current: CurrentStaff,
    *,
    page: int,
    page_size: int,
    status: TaskStatus | None = None,
) -> tuple[list[Task], int]:
    criteria = [Task.archived_at.is_(None), _task_scope(current)]
    if status is not None:
        criteria.append(Task.status == status)
    total = db.scalar(select(func.count()).select_from(Task).where(*criteria)) or 0
    items = list(
        db.scalars(
            select(Task)
            .where(*criteria)
            .order_by(Task.due_date.asc().nullslast(), Task.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, total


def create_task(db: Session, current: CurrentStaff, payload: TaskCreate) -> Task:
    if Permission.TASK_WRITE not in current.permissions and payload.owner_id != current.staff.id:
        raise ApiError(
            status_code=403,
            code="TASK_OWNERSHIP_REQUIRED",
            message="Puoi creare attività solo per te stesso.",
        )
    task = Task(**payload.model_dump(), created_by_id=current.staff.id)
    task.completed_at = completion_timestamp(task.status, None)
    db.add(task)
    db.flush()
    return task


def update_task(db: Session, current: CurrentStaff, task_id: UUID, payload: TaskPatch) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.archived_at is not None:
        raise ApiError(status_code=404, code="TASK_NOT_FOUND", message="Attività non trovata.")
    full_write = Permission.TASK_WRITE in current.permissions
    if not full_write and task.owner_id != current.staff.id:
        raise ApiError(
            status_code=403,
            code="TASK_OWNERSHIP_REQUIRED",
            message="Puoi modificare solo le tue attività.",
        )
    values = payload.model_dump(exclude_unset=True, exclude={"archive"})
    if not full_write and values.get("owner_id", task.owner_id) != current.staff.id:
        raise ApiError(
            status_code=403,
            code="TASK_ASSIGN_DENIED",
            message="Non puoi riassegnare questa attività.",
        )
    for key, value in values.items():
        setattr(task, key, value)
    task.completed_at = completion_timestamp(task.status, task.completed_at)
    if payload.archive:
        task.archived_at = datetime.now(UTC)
        task.archived_by_id = current.staff.id
    db.flush()
    return task


def list_notifications(db: Session, staff_id: UUID) -> tuple[list[Notification], int]:
    items = list(
        db.scalars(
            select(Notification)
            .where(Notification.recipient_id == staff_id)
            .order_by(Notification.created_at.desc())
            .limit(100)
        )
    )
    unread = (
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.recipient_id == staff_id, Notification.read_at.is_(None))
        )
        or 0
    )
    return items, unread
