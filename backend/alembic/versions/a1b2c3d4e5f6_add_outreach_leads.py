"""add outreach_leads table

Revision ID: a1b2c3d4e5f6
Revises: 017e7bb54870
Create Date: 2026-11-07

New table for persisted outreach leads. One row per attempted contact;
status transitions: pending_approval -> approved -> sent (or -> skipped/failed).
Foreign keys cascade from users (delete user -> delete leads) and set-null
from opportunities (delete opportunity -> preserve lead history).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "017e7bb54870"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "outreach_leads",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunities.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_title", sa.String(255), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_linkedin", sa.String(500), nullable=True),
        sa.Column("contact_source", sa.String(50), nullable=True),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="pending_approval",
        ),
        sa.Column("email_subject", sa.String(500), nullable=True),
        sa.Column("email_draft", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("credit_cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index("ix_outreach_leads_user_id", "outreach_leads", ["user_id"])
    op.create_index(
        "ix_outreach_leads_opportunity_id", "outreach_leads", ["opportunity_id"]
    )
    op.create_index("ix_outreach_leads_run_id", "outreach_leads", ["run_id"])
    op.create_index("ix_outreach_leads_status", "outreach_leads", ["status"])
    op.create_index(
        "ix_outreach_leads_user_status", "outreach_leads", ["user_id", "status"]
    )


def downgrade() -> None:
    op.drop_index("ix_outreach_leads_user_status", table_name="outreach_leads")
    op.drop_index("ix_outreach_leads_status", table_name="outreach_leads")
    op.drop_index("ix_outreach_leads_run_id", table_name="outreach_leads")
    op.drop_index("ix_outreach_leads_opportunity_id", table_name="outreach_leads")
    op.drop_index("ix_outreach_leads_user_id", table_name="outreach_leads")
    op.drop_table("outreach_leads")
