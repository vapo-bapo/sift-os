from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.company.models import Notification, TaskStatus
from app.company.schemas import (
    NotificationList,
    NotificationResponse,
    ObjectiveCreate,
    ObjectiveList,
    ObjectivePatch,
    ObjectiveResponse,
    TaskCreate,
    TaskList,
    TaskPatch,
    TaskResponse,
)
from app.company.service import (
    create_objective,
    create_task,
    list_notifications,
    list_objectives,
    list_tasks,
    update_objective,
    update_task,
)
from app.core.errors import ApiError
from app.db.session import get_db
from app.staff.dependencies import CurrentStaff, get_current_staff, require_csrf, require_permission
from app.staff.permissions import Permission

router = APIRouter(prefix="/api", tags=["company"])


@router.get("/objectives", response_model=ObjectiveList)
def objectives(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(require_permission(Permission.OBJECTIVE_READ))],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> ObjectiveList:
    del current
    items, total = list_objectives(db, page=page, page_size=page_size)
    return ObjectiveList(items=items, total=total, page=page, page_size=page_size)


@router.post("/objectives", response_model=ObjectiveResponse, status_code=201)
def objective_create(
    payload: ObjectiveCreate,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(require_csrf)],
) -> ObjectiveResponse:
    if Permission.OBJECTIVE_WRITE not in current.permissions:
        raise ApiError(
            status_code=403, code="PERMISSION_DENIED", message="Non hai i permessi necessari."
        )
    result = create_objective(db, payload)
    db.commit()
    db.refresh(result)
    return ObjectiveResponse.model_validate(result)


@router.patch("/objectives/{objective_id}", response_model=ObjectiveResponse)
def objective_update(
    objective_id: UUID,
    payload: ObjectivePatch,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(require_csrf)],
) -> ObjectiveResponse:
    if Permission.OBJECTIVE_WRITE not in current.permissions:
        raise ApiError(
            status_code=403, code="PERMISSION_DENIED", message="Non hai i permessi necessari."
        )
    result = update_objective(db, objective_id, payload, current.staff.id)
    db.commit()
    db.refresh(result)
    return ObjectiveResponse.model_validate(result)


@router.get("/tasks", response_model=TaskList)
def tasks(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(require_permission(Permission.TASK_READ))],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: TaskStatus | None = None,
) -> TaskList:
    items, total = list_tasks(db, current, page=page, page_size=page_size, status=status)
    return TaskList(items=items, total=total, page=page, page_size=page_size)


@router.post("/tasks", response_model=TaskResponse, status_code=201)
def task_create(
    payload: TaskCreate,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(require_csrf)],
) -> TaskResponse:
    if not ({Permission.TASK_WRITE, Permission.TASK_WRITE_OWN} & current.permissions):
        raise ApiError(
            status_code=403, code="PERMISSION_DENIED", message="Non hai i permessi necessari."
        )
    result = create_task(db, current, payload)
    db.commit()
    db.refresh(result)
    return TaskResponse.model_validate(result)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def task_update(
    task_id: UUID,
    payload: TaskPatch,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(require_csrf)],
) -> TaskResponse:
    result = update_task(db, current, task_id, payload)
    db.commit()
    db.refresh(result)
    return TaskResponse.model_validate(result)


@router.get("/notifications", response_model=NotificationList)
def notifications(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(get_current_staff)],
) -> NotificationList:
    items, unread = list_notifications(db, current.staff.id)
    return NotificationList(items=items, unread=unread)


@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse)
def notification_read(
    notification_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(require_csrf)],
) -> NotificationResponse:
    item = db.get(Notification, notification_id)
    if item is None or item.recipient_id != current.staff.id:
        raise ApiError(
            status_code=404, code="NOTIFICATION_NOT_FOUND", message="Notifica non trovata."
        )
    item.read_at = datetime.now(UTC)
    db.commit()
    db.refresh(item)
    return NotificationResponse.model_validate(item)
