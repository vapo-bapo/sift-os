"""Create partner management and product operations.

Revision ID: 20260909_0003
Revises: 20260909_0002
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260909_0003"
down_revision: str | None = "20260909_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

partner_status = postgresql.ENUM(
    "prospect",
    "negotiating",
    "signed",
    "onboarding",
    "active",
    "inactive",
    "terminated",
    name="partner_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    partner_status.create(bind, checkfirst=False)

    op.create_table(
        "partners",
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
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("legal_name", sa.String(length=240), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("domain", sa.String(length=253), nullable=True),
        sa.Column("owner_staff_id", sa.Uuid(), nullable=True),
        sa.Column("status", partner_status, nullable=False),
        sa.Column("notes", sa.String(length=4000), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_customer_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["archived_by"], ["staff_members.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_staff_id"], ["staff_members.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_partners_archived_at", "partners", ["archived_at"])
    op.create_index("ix_partners_domain", "partners", ["domain"])
    op.create_index("ix_partners_email", "partners", ["email"])
    op.create_index("ix_partners_name", "partners", ["name"])
    op.create_index("ix_partners_owner_staff_id", "partners", ["owner_staff_id"])
    op.create_index("ix_partners_owner_status", "partners", ["owner_staff_id", "status"])

    op.create_table(
        "partner_agreements",
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
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("partner_share_bps", sa.Integer(), nullable=False),
        sa.Column("sift_share_bps", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("terms", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "partner_share_bps >= 0 AND partner_share_bps <= 10000",
            name="ck_partner_agreement_partner_bps",
        ),
        sa.CheckConstraint(
            "sift_share_bps >= 0 AND sift_share_bps <= 10000", name="ck_partner_agreement_sift_bps"
        ),
        sa.CheckConstraint(
            "partner_share_bps + sift_share_bps = 10000", name="ck_partner_agreement_total_bps"
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_partner_agreement_dates",
        ),
        sa.ForeignKeyConstraint(["archived_by"], ["staff_members.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["staff_members.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("partner_id", "version", name="uq_partner_agreement_version"),
    )
    op.create_index(
        "ix_partner_agreements_effective", "partner_agreements", ["partner_id", "effective_from"]
    )

    op.create_table(
        "partner_clients",
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
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("agreement_id", sa.Uuid(), nullable=False),
        sa.Column("external_client_id", sa.Uuid(), nullable=False),
        sa.Column("client_name", sa.String(length=240), nullable=False),
        sa.Column("attributed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gross_revenue_cents", sa.Integer(), nullable=False),
        sa.Column("partner_share_cents", sa.Integer(), nullable=False),
        sa.Column("sift_share_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by", sa.Uuid(), nullable=True),
        sa.CheckConstraint("gross_revenue_cents >= 0", name="ck_partner_client_gross_cents"),
        sa.CheckConstraint("partner_share_cents >= 0", name="ck_partner_client_partner_cents"),
        sa.CheckConstraint("sift_share_cents >= 0", name="ck_partner_client_sift_cents"),
        sa.CheckConstraint(
            "partner_share_cents + sift_share_cents = gross_revenue_cents",
            name="ck_partner_client_split_cents",
        ),
        sa.ForeignKeyConstraint(["agreement_id"], ["partner_agreements.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["archived_by"], ["staff_members.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("partner_id", "external_client_id", name="uq_partner_external_client"),
    )
    op.create_index(
        "ix_partner_clients_attributed", "partner_clients", ["partner_id", "attributed_at"]
    )
    op.create_index(
        "ix_partner_clients_external_client_id", "partner_clients", ["external_client_id"]
    )

    op.create_table(
        "products",
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
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["archived_by"], ["staff_members.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    product_table = sa.table(
        "products",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("active", sa.Boolean()),
    )
    op.bulk_insert(
        product_table,
        [
            {
                "id": "ee5cb456-3ac2-4c55-8470-d2a10462c63e",
                "code": "ARGUS",
                "name": "ARGUS",
                "active": True,
            },
            {
                "id": "cbe6a55b-f7f2-4700-95fe-c4cab32c1ed2",
                "code": "LYNX",
                "name": "LYNX",
                "active": True,
            },
        ],
    )

    op.create_table(
        "product_service_credentials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("rotated_from_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["staff_members.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["revoked_by"], ["staff_members.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["rotated_from_id"], ["product_service_credentials.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_digest"),
    )
    op.create_index(
        "ix_product_credentials_active", "product_service_credentials", ["product_id", "revoked_at"]
    )

    op.create_table(
        "product_runs",
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
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("external_run_id", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("cost_cents", sa.Integer(), nullable=False),
        sa.Column("units", sa.Integer(), nullable=False),
        sa.Column("run_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint("event_count >= 0", name="ck_product_run_event_count"),
        sa.CheckConstraint("cost_cents >= 0", name="ck_product_run_cost_cents"),
        sa.CheckConstraint("units >= 0", name="ck_product_run_units"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "external_run_id", name="uq_product_external_run"),
    )
    op.create_index("ix_product_runs_started", "product_runs", ["product_id", "started_at"])
    op.create_index("ix_product_runs_status", "product_runs", ["product_id", "status"])

    op.create_table(
        "product_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("product_run_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("external_run_id", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=True),
        sa.Column("cost_cents", sa.Integer(), nullable=False),
        sa.Column("units", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint("schema_version > 0", name="ck_product_event_schema_version"),
        sa.CheckConstraint("cost_cents >= 0", name="ck_product_event_cost_cents"),
        sa.CheckConstraint("units >= 0", name="ck_product_event_units"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_run_id"], ["product_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_product_events_product_occurred", "product_events", ["product_id", "occurred_at"]
    )
    op.create_index("ix_product_events_run", "product_events", ["product_run_id"])
    op.create_index("ix_product_events_type", "product_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_product_events_type", table_name="product_events")
    op.drop_index("ix_product_events_run", table_name="product_events")
    op.drop_index("ix_product_events_product_occurred", table_name="product_events")
    op.drop_table("product_events")
    op.drop_index("ix_product_runs_status", table_name="product_runs")
    op.drop_index("ix_product_runs_started", table_name="product_runs")
    op.drop_table("product_runs")
    op.drop_index("ix_product_credentials_active", table_name="product_service_credentials")
    op.drop_table("product_service_credentials")
    op.drop_table("products")
    op.drop_index("ix_partner_clients_external_client_id", table_name="partner_clients")
    op.drop_index("ix_partner_clients_attributed", table_name="partner_clients")
    op.drop_table("partner_clients")
    op.drop_index("ix_partner_agreements_effective", table_name="partner_agreements")
    op.drop_table("partner_agreements")
    op.drop_index("ix_partners_owner_status", table_name="partners")
    op.drop_index("ix_partners_owner_staff_id", table_name="partners")
    op.drop_index("ix_partners_name", table_name="partners")
    op.drop_index("ix_partners_email", table_name="partners")
    op.drop_index("ix_partners_domain", table_name="partners")
    op.drop_index("ix_partners_archived_at", table_name="partners")
    op.drop_table("partners")
    partner_status.drop(op.get_bind(), checkfirst=False)
