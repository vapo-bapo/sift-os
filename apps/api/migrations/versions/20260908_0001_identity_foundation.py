"""Create identity and audit foundation.

Revision ID: 20260908_0001
Revises:
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


department = postgresql.ENUM("sales", "coding", name="department", create_type=False)
staff_role = postgresql.ENUM(
    "ceo", "admin", "sales_lead", "sales", "coding", name="staff_role", create_type=False
)
audit_result = postgresql.ENUM("success", "failure", name="audit_result", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    department.create(bind, checkfirst=False)
    staff_role.create(bind, checkfirst=False)
    audit_result.create(bind, checkfirst=False)

    op.create_table(
        "staff_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("platform_user_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=201), nullable=False),
        sa.Column("department", department, nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_staff_members_platform_user_id", "staff_members", ["platform_user_id"], unique=True
    )

    op.create_table(
        "staff_member_roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("staff_member_id", sa.Uuid(), nullable=False),
        sa.Column("role", staff_role, nullable=False),
        sa.ForeignKeyConstraint(["staff_member_id"], ["staff_members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("staff_member_id", "role", name="uq_staff_role"),
    )

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("staff_member_id", sa.Uuid(), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("csrf_nonce_digest", sa.String(length=64), nullable=False),
        sa.Column("platform_assertion_jti", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["staff_member_id"], ["staff_members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform_assertion_jti", name="uq_user_sessions_assertion_jti"),
        sa.UniqueConstraint("token_digest", name="uq_user_sessions_token_digest"),
    )
    op.create_index(
        "ix_user_sessions_staff_member_id", "user_sessions", ["staff_member_id"], unique=False
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_staff_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("previous", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent_summary", sa.String(length=256), nullable=True),
        sa.Column("result", audit_result, nullable=False),
        sa.ForeignKeyConstraint(["actor_staff_id"], ["staff_members.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_actor_staff_id", "audit_logs", ["actor_staff_id"], unique=False)
    op.create_index("ix_audit_logs_occurred_at", "audit_logs", ["occurred_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_occurred_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_staff_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_user_sessions_staff_member_id", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_table("staff_member_roles")
    op.drop_index("ix_staff_members_platform_user_id", table_name="staff_members")
    op.drop_table("staff_members")

    bind = op.get_bind()
    audit_result.drop(bind, checkfirst=False)
    staff_role.drop(bind, checkfirst=False)
    department.drop(bind, checkfirst=False)
