"""backfill users profile columns (repair drift)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-07

The User model declares 8 profile columns that were never created in the DB
(alembic_version was stamped at 017e7bb54870 without executing the DDL).
This migration adds them idempotently so future migrations on users work,
and so auth/profile endpoints can query the table.

Downgrade removes the columns. Do NOT run downgrade in production unless
you intend to lose profile data.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_COLUMNS = [
    ("bio", sa.Text()),
    ("skills", sa.Text()),
    ("target_roles", sa.Text()),
    ("location", sa.String(255)),
    ("github_url", sa.String(500)),
    ("linkedin_url", sa.String(500)),
    ("college", sa.String(255)),
    ("graduation_year", sa.String(10)),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {col["name"] for col in inspector.get_columns("users")}
    for name, type_ in _COLUMNS:
        if name not in existing:
            op.add_column("users", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {col["name"] for col in inspector.get_columns("users")}
    for name, _ in reversed(_COLUMNS):
        if name in existing:
            op.drop_column("users", name)
