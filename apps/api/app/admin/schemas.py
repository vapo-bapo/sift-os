from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    actor_staff_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    occurred_at: datetime
    previous: dict[str, Any] | None
    new: dict[str, Any] | None
    request_id: str
    result: str


class AuditLogList(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
