from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.models import AuditLog, AuditResult


def record_audit_log(
    session: Session,
    *,
    actor_staff_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None,
    previous: dict[str, Any] | None,
    new: dict[str, Any] | None,
    request_id: str,
    ip_address: str | None,
    user_agent_summary: str | None,
    result: AuditResult,
) -> AuditLog:
    audit_log = AuditLog(
        actor_staff_id=actor_staff_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        previous=previous,
        new=new,
        request_id=request_id,
        ip_address=ip_address,
        user_agent_summary=user_agent_summary,
        result=result,
    )
    session.add(audit_log)
    return audit_log
