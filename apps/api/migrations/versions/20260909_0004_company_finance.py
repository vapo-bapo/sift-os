"""Create company operations and finance tables.

Revision ID: 20260909_0004
Revises: 20260909_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260909_0004"
down_revision: str | None = "20260909_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

workstream = postgresql.ENUM(
    "sales",
    "argus",
    "lynx",
    "legal",
    "finance",
    "coding",
    "company",
    name="workstream",
    create_type=False,
)
objective_status = postgresql.ENUM(
    "planned",
    "active",
    "at_risk",
    "completed",
    "archived",
    name="objective_status",
    create_type=False,
)
task_priority = postgresql.ENUM("P0", "P1", "P2", "P3", name="task_priority", create_type=False)
task_status = postgresql.ENUM(
    "backlog",
    "todo",
    "in_progress",
    "blocked",
    "review",
    "done",
    name="task_status",
    create_type=False,
)
financial_entry_type = postgresql.ENUM(
    "revenue",
    "recurring_cost",
    "one_time_cost",
    "api_cost",
    "cloud_cost",
    "professional_service",
    "partner_commission",
    "other",
    name="financial_entry_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    objective_status.create(bind, checkfirst=False)
    workstream.create(bind, checkfirst=False)
    task_priority.create(bind, checkfirst=False)
    task_status.create(bind, checkfirst=False)
    financial_entry_type.create(bind, checkfirst=False)

    op.create_table(
        "objectives",
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
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("department", workstream, nullable=False),
        sa.Column("status", objective_status, nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date()),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("archived_by_id", sa.Uuid()),
        sa.CheckConstraint("progress >= 0 AND progress <= 100", name="ck_objective_progress"),
        sa.ForeignKeyConstraint(["owner_id"], ["staff_members.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["archived_by_id"], ["staff_members.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("owner_id", "department", "status", "archived_at"):
        op.create_index(f"ix_objectives_{column}", "objectives", [column])

    op.create_table(
        "tasks",
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
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("objective_id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("department", workstream, nullable=False),
        sa.Column("priority", task_priority, nullable=False),
        sa.Column("status", task_status, nullable=False),
        sa.Column("due_date", sa.Date()),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("archived_by_id", sa.Uuid()),
        sa.ForeignKeyConstraint(["objective_id"], ["objectives.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["staff_members.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["staff_members.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["archived_by_id"], ["staff_members.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "objective_id",
        "owner_id",
        "department",
        "priority",
        "status",
        "due_date",
        "archived_at",
    ):
        op.create_index(f"ix_tasks_{column}", "tasks", [column])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("recipient_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("entity_type", sa.String(80)),
        sa.Column("entity_id", sa.Uuid()),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["recipient_id"], ["staff_members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("recipient_id", "event_type", "read_at"):
        op.create_index(f"ix_notifications_{column}", "notifications", [column])

    op.create_table(
        "financial_entries",
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
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("entry_type", financial_entry_type, nullable=False),
        sa.Column("category", sa.String(120), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("account_id", sa.Uuid()),
        sa.Column("partner_id", sa.Uuid()),
        sa.Column("product_id", sa.Uuid()),
        sa.Column("recurring", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(160)),
        sa.Column("note", sa.Text()),
        sa.Column("created_by_id", sa.Uuid()),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("archived_by_id", sa.Uuid()),
        sa.CheckConstraint("amount_cents > 0", name="ck_financial_entry_amount_positive"),
        sa.ForeignKeyConstraint(["account_id"], ["crm_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["staff_members.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["archived_by_id"], ["staff_members.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "date",
        "entry_type",
        "category",
        "account_id",
        "partner_id",
        "product_id",
        "created_by_id",
        "archived_at",
    ):
        op.create_index(f"ix_financial_entries_{column}", "financial_entries", [column])

    op.create_table(
        "financial_snapshots",
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
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("cash_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("created_by_id", sa.Uuid()),
        sa.ForeignKeyConstraint(["created_by_id"], ["staff_members.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_financial_snapshots_date", "financial_snapshots", ["date"])


def downgrade() -> None:
    op.drop_index("ix_financial_snapshots_date", table_name="financial_snapshots")
    op.drop_table("financial_snapshots")
    for column in (
        "archived_at",
        "created_by_id",
        "product_id",
        "partner_id",
        "account_id",
        "category",
        "entry_type",
        "date",
    ):
        op.drop_index(f"ix_financial_entries_{column}", table_name="financial_entries")
    op.drop_table("financial_entries")
    for column in ("read_at", "event_type", "recipient_id"):
        op.drop_index(f"ix_notifications_{column}", table_name="notifications")
    op.drop_table("notifications")
    for column in (
        "archived_at",
        "due_date",
        "status",
        "priority",
        "department",
        "owner_id",
        "objective_id",
    ):
        op.drop_index(f"ix_tasks_{column}", table_name="tasks")
    op.drop_table("tasks")
    for column in ("archived_at", "status", "department", "owner_id"):
        op.drop_index(f"ix_objectives_{column}", table_name="objectives")
    op.drop_table("objectives")

    bind = op.get_bind()
    financial_entry_type.drop(bind, checkfirst=False)
    task_status.drop(bind, checkfirst=False)
    task_priority.drop(bind, checkfirst=False)
    objective_status.drop(bind, checkfirst=False)
    workstream.drop(bind, checkfirst=False)
