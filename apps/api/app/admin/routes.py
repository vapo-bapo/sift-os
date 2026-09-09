from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.admin.schemas import AuditLogList
from app.audit.models import AuditLog
from app.db.session import get_db
from app.staff.dependencies import CurrentStaff, require_permission
from app.staff.permissions import Permission

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/audit", response_model=AuditLogList)
def audit_log(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(require_permission(Permission.AUDIT_READ))],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: str | None = None,
    entity_type: str | None = None,
) -> AuditLogList:
    del current
    criteria = []
    if action:
        criteria.append(AuditLog.action == action)
    if entity_type:
        criteria.append(AuditLog.entity_type == entity_type)
    total = db.scalar(select(func.count()).select_from(AuditLog).where(*criteria)) or 0
    items = list(
        db.scalars(
            select(AuditLog)
            .where(*criteria)
            .order_by(AuditLog.occurred_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return AuditLogList(items=items, total=total, page=page, page_size=page_size)
