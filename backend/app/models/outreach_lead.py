"""Persisted outreach lead — one row per attempted contact.

Each row records what the agent found, what it drafted, whether the user
approved, and whether the email was actually sent. Rows are created by the
SAVE_LEAD tool (pending_approval) and updated by the SEND_EMAIL tool (sent)
or the reject path (skipped).

Status values mirror schemas.ApprovalDecision semantics but are stored as
plain strings with a bounded length — we validate at the app layer rather
than introducing a PostgreSQL enum type that complicates migrations.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class OutreachStatus(str, Enum):
    """Lifecycle of a single outreach lead."""
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class OutreachLead(Base, TimestampMixin):
    """A single lead the agent is (or was) pursuing on behalf of a user."""

    __tablename__ = "outreach_leads"
    __table_args__ = (
        # Fast lookup: "show me all pending leads for this user"
        Index("ix_outreach_leads_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Opaque link to the agent run that produced this lead. No FK because
    # agent runs are held in memory during the hackathon build; persist later
    # by adding an agent_runs table and pointing this at it.
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    # Contact info — all nullable because the agent may only find some fields.
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_linkedin: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_source: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        doc="Where the contact came from: crustdata | scraper | manual | unknown",
    )

    # Workflow state.
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=OutreachStatus.PENDING_APPROVAL.value,
        index=True,
    )
    email_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Cost accounting for Crustdata credits spent on this lead.
    credit_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<OutreachLead id={self.id} status={self.status} "
            f"to={self.contact_email}>"
        )
