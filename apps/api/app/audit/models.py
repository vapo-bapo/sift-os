from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin, enum_type


class AuditResult(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"

    actor_staff_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff_members.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(Uuid)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    previous: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    new: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent_summary: Mapped[str | None] = mapped_column(String(256))
    result: Mapped[AuditResult] = mapped_column(
        enum_type(AuditResult, "audit_result"), nullable=False
    )
