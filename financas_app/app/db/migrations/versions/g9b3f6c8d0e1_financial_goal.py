"""financial_goal table

Revision ID: g9b3f6c8d0e1
Revises: f8a2e5b6c7d9
Create Date: 2026-04-16 12:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision = "g9b3f6c8d0e1"
down_revision = "f8a2e5b6c7d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "financial_goal" in insp.get_table_names():
        return
    op.create_table(
        "financial_goal",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=False),
        sa.Column("target_cents", sa.Integer(), nullable=False),
        sa.Column("saved_cents", sa.Integer(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_financial_goal_user_id"), "financial_goal", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_financial_goal_user_id"), table_name="financial_goal")
    op.drop_table("financial_goal")
