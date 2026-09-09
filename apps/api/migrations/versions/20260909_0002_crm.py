"""Create native CRM tables.

Revision ID: 20260909_0002
Revises: 20260908_0001
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260909_0002"
down_revision: str | None = "20260908_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

account_type = postgresql.ENUM(
    "prospect_agency",
    "partner_agency",
    "direct_prospect",
    "direct_customer",
    "case_study",
    "customer",
    "other",
    name="crm_account_type",
    create_type=False,
)
account_status = postgresql.ENUM(
    "new", "active", "inactive", name="crm_account_status", create_type=False
)
preferred_channel = postgresql.ENUM(
    "email",
    "phone",
    "linkedin",
    "whatsapp",
    "other",
    name="crm_preferred_channel",
    create_type=False,
)
opportunity_stage = postgresql.ENUM(
    "prospect",
    "contacted",
    "qualified",
    "meeting",
    "demo",
    "proposal",
    "negotiation",
    "partner_signed",
    "partner_activated",
    "won",
    "lost",
    "disqualified",
    name="crm_opportunity_stage",
    create_type=False,
)
opportunity_status = postgresql.ENUM(
    "open", "won", "lost", "disqualified", name="crm_opportunity_status", create_type=False
)
opportunity_channel = postgresql.ENUM(
    "agency_partner",
    "direct_sales",
    "referral",
    "inbound",
    "other",
    name="crm_opportunity_channel",
    create_type=False,
)
activity_type = postgresql.ENUM(
    "call",
    "email",
    "linkedin",
    "whatsapp",
    "meeting",
    "demo",
    "proposal",
    "follow_up",
    "note",
    "other",
    name="crm_activity_type",
    create_type=False,
)


def _timestamps() -> list[sa.Column[object]]:
    return [
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
    ]


def upgrade() -> None:
    bind = op.get_bind()
    for enum in (
        account_type,
        account_status,
        preferred_channel,
        opportunity_stage,
        opportunity_status,
        opportunity_channel,
        activity_type,
    ):
        enum.create(bind, checkfirst=False)

    op.create_table(
        "crm_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("domain", sa.String(253)),
        sa.Column("normalized_domain", sa.String(253)),
        sa.Column("website", sa.String(500)),
        sa.Column("industry", sa.String(100)),
        sa.Column("company_size", sa.String(50)),
        sa.Column("country", sa.String(2)),
        sa.Column("city", sa.String(100)),
        sa.Column("account_type", account_type, nullable=False),
        sa.Column("source", sa.String(100)),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("status", account_status, nullable=False),
        sa.Column("lead_score", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "lead_score >= 0 AND lead_score <= 100", name="ck_crm_account_lead_score"
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["staff_members.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_accounts_owner_id", "crm_accounts", ["owner_id"])
    op.create_index("ix_crm_accounts_archived_at", "crm_accounts", ["archived_at"])
    op.create_index("ix_crm_accounts_owner_status", "crm_accounts", ["owner_id", "status"])
    op.create_index(
        "uq_crm_accounts_normalized_domain_active",
        "crm_accounts",
        ["normalized_domain"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL AND normalized_domain IS NOT NULL"),
    )

    op.create_table(
        "crm_contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("normalized_name", sa.String(201), nullable=False),
        sa.Column("role", sa.String(120)),
        sa.Column("email", sa.String(320)),
        sa.Column("normalized_email", sa.String(320)),
        sa.Column("phone", sa.String(50)),
        sa.Column("normalized_phone", sa.String(50)),
        sa.Column("linkedin_url", sa.String(500)),
        sa.Column("preferred_channel", preferred_channel),
        sa.Column("is_decision_maker", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.ForeignKeyConstraint(["account_id"], ["crm_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_email", name="uq_crm_contacts_normalized_email"),
        sa.UniqueConstraint("account_id", "normalized_phone", name="uq_crm_contacts_account_phone"),
        sa.UniqueConstraint("account_id", "normalized_name", name="uq_crm_contacts_account_name"),
    )
    op.create_index("ix_crm_contacts_account", "crm_contacts", ["account_id"])

    op.create_table(
        "crm_opportunities",
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("primary_contact_id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("stage", opportunity_stage, nullable=False),
        sa.Column("status", opportunity_status, nullable=False),
        sa.Column("estimated_value_cents", sa.Integer(), nullable=False),
        sa.Column("weighted_value_cents", sa.Integer(), nullable=False),
        sa.Column("probability", sa.Integer(), nullable=False),
        sa.Column("expected_close_date", sa.Date()),
        sa.Column("source", sa.String(100)),
        sa.Column("channel", opportunity_channel, nullable=False),
        sa.Column("interested_products", postgresql.ARRAY(sa.String(100)), nullable=False),
        sa.Column("next_action", sa.String(500)),
        sa.Column("next_action_at", sa.DateTime(timezone=True)),
        sa.Column("lost_reason", sa.Text()),
        sa.Column("won_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("estimated_value_cents >= 0", name="ck_crm_opportunity_value"),
        sa.CheckConstraint("probability >= 0 AND probability <= 100", name="ck_crm_probability"),
        sa.CheckConstraint(
            "weighted_value_cents = (estimated_value_cents * probability) / 100",
            name="ck_crm_weighted_value",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["crm_accounts.id"]),
        sa.ForeignKeyConstraint(["primary_contact_id"], ["crm_contacts.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["staff_members.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_opportunities_account_id", "crm_opportunities", ["account_id"])
    op.create_index("ix_crm_opportunities_owner_id", "crm_opportunities", ["owner_id"])
    op.create_index("ix_crm_opportunities_owner_stage", "crm_opportunities", ["owner_id", "stage"])
    op.create_index("ix_crm_opportunities_next_action", "crm_opportunities", ["next_action_at"])

    op.create_table(
        "opportunity_stage_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("previous_stage", opportunity_stage),
        sa.Column("new_stage", opportunity_stage, nullable=False),
        sa.Column("changed_by", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["crm_opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by"], ["staff_members.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_stage_history_opportunity_created",
        "opportunity_stage_history",
        ["opportunity_id", "created_at"],
    )

    op.create_table(
        "crm_activities",
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.Column("account_id", sa.Uuid()),
        sa.Column("contact_id", sa.Uuid()),
        sa.Column("opportunity_id", sa.Uuid()),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("activity_type", activity_type, nullable=False),
        sa.Column("outcome", sa.String(200)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("next_action", sa.String(500)),
        sa.Column("next_action_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "account_id IS NOT NULL OR contact_id IS NOT NULL OR opportunity_id IS NOT NULL",
            name="ck_crm_activity_subject",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["crm_accounts.id"]),
        sa.ForeignKeyConstraint(["contact_id"], ["crm_contacts.id"]),
        sa.ForeignKeyConstraint(["opportunity_id"], ["crm_opportunities.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["staff_members.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_activities_account_id", "crm_activities", ["account_id"])
    op.create_index("ix_crm_activities_owner_id", "crm_activities", ["owner_id"])
    op.create_index("ix_crm_activities_owner_started", "crm_activities", ["owner_id", "started_at"])
    op.create_index(
        "ix_crm_activities_owner_next", "crm_activities", ["owner_id", "next_action_at"]
    )

    op.create_table(
        "crm_case_study_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("baseline", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("runs", sa.Integer()),
        sa.Column("leads", sa.Integer()),
        sa.Column("qualified", sa.Integer()),
        sa.Column("meetings", sa.Integer()),
        sa.Column("hours_saved", sa.Numeric(12, 2)),
        sa.Column("conversion", sa.Numeric(7, 4)),
        sa.Column("notes", sa.Text()),
        sa.Column("period_start", sa.Date()),
        sa.Column("period_end", sa.Date()),
        sa.CheckConstraint("runs IS NULL OR runs >= 0", name="ck_case_study_runs"),
        sa.CheckConstraint("leads IS NULL OR leads >= 0", name="ck_case_study_leads"),
        sa.CheckConstraint("qualified IS NULL OR qualified >= 0", name="ck_case_study_qualified"),
        sa.CheckConstraint("meetings IS NULL OR meetings >= 0", name="ck_case_study_meetings"),
        sa.CheckConstraint("hours_saved IS NULL OR hours_saved >= 0", name="ck_case_study_hours"),
        sa.CheckConstraint(
            "conversion IS NULL OR (conversion >= 0 AND conversion <= 100)",
            name="ck_case_study_conversion",
        ),
        sa.CheckConstraint(
            "period_end IS NULL OR period_start IS NULL OR period_end >= period_start",
            name="ck_case_study_period",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["crm_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", name="uq_crm_case_study_metrics_account"),
    )


def downgrade() -> None:
    op.drop_table("crm_case_study_metrics")
    op.drop_table("crm_activities")
    op.drop_table("opportunity_stage_history")
    op.drop_table("crm_opportunities")
    op.drop_table("crm_contacts")
    op.drop_table("crm_accounts")
    bind = op.get_bind()
    for enum in (
        activity_type,
        opportunity_channel,
        opportunity_status,
        opportunity_stage,
        preferred_channel,
        account_status,
        account_type,
    ):
        enum.drop(bind, checkfirst=False)
