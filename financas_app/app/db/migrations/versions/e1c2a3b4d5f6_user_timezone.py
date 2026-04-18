"""user timezone

Revision ID: e1c2a3b4d5f6
Revises: g9b3f6c8d0e1
Create Date: 2026-04-16 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision = "e1c2a3b4d5f6"
down_revision = "g9b3f6c8d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns("user")]
    if "timezone" in cols:
        return
    op.add_column("user", sa.Column("timezone", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "timezone")

