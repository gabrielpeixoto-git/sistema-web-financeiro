"""transaction transfer_group_id

Revision ID: c5f9b2e1a3d4
Revises: b4e8a1c2d3f4
Create Date: 2026-04-15 21:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision = "c5f9b2e1a3d4"
down_revision = "b4e8a1c2d3f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns("transaction")]
    if "transfer_group_id" in cols:
        return
    op.add_column(
        "transaction",
        sa.Column("transfer_group_id", sqlmodel.sql.sqltypes.AutoString(length=36), nullable=True),
    )
    op.create_index(
        op.f("ix_transaction_transfer_group_id"),
        "transaction",
        ["transfer_group_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_transaction_transfer_group_id"), table_name="transaction")
    op.drop_column("transaction", "transfer_group_id")
