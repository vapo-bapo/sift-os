from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class UserSession(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "user_sessions"

    staff_member_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff_members.id", ondelete="CASCADE"), index=True
    )
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    csrf_nonce_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    platform_assertion_jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
