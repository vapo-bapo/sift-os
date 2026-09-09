from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.company.models import ObjectiveStatus, TaskPriority, TaskStatus, Workstream


class ObjectiveCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str | None = None
    owner_id: UUID
    department: Workstream
    status: ObjectiveStatus = ObjectiveStatus.PLANNED
    start_date: Date
    due_date: Date | None = None
    progress: int = Field(default=0, ge=0, le=100)


class ObjectivePatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = None
    owner_id: UUID | None = None
    department: Workstream | None = None
    status: ObjectiveStatus | None = None
    start_date: Date | None = None
    due_date: Date | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    archive: bool = False


class ObjectiveResponse(ObjectiveCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str | None = None
    objective_id: UUID | None = None
    owner_id: UUID
    department: Workstream
    priority: TaskPriority = TaskPriority.P2
    status: TaskStatus = TaskStatus.TODO
    due_date: Date | None = None


class TaskPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = None
    objective_id: UUID | None = None
    owner_id: UUID | None = None
    department: Workstream | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    due_date: Date | None = None
    archive: bool = False


class TaskResponse(TaskCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    archived_at: datetime | None


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_type: str
    title: str
    body: str | None
    entity_type: str | None
    entity_id: UUID | None
    created_at: datetime
    read_at: datetime | None


class ObjectiveList(BaseModel):
    items: list[ObjectiveResponse]
    total: int
    page: int
    page_size: int


class TaskList(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    page_size: int


class NotificationList(BaseModel):
    items: list[NotificationResponse]
    unread: int
