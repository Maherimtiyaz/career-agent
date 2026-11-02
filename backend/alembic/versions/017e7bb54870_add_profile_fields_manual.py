"""add profile fields manual

Revision ID: 017e7bb54870
Revises: 41e5b4937ddb
Create Date: 2026-07-21 17:00:59.193562

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '017e7bb54870'
down_revision: Union[str, None] = '41e5b4937ddb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
