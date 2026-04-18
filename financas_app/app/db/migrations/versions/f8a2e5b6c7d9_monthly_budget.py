"""monthly_budget table

Revision ID: f8a2e5b6c7d9
Revises: d6a0c3f2b4e5
Create Date: 2026-04-15 23:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision = "f8a2e5b6c7d9"
down_revision = "d6a0c3f2b4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "monthly_budget" in insp.get_table_names():
        return
    op.create_table(
        "monthly_budget",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("limit_cents", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "category_id", "year", "month", name="uq_monthly_budget_user_cat_ym"),
    )
    op.create_index(op.f("ix_monthly_budget_user_id"), "monthly_budget", ["user_id"], unique=False)
    op.create_index(op.f("ix_monthly_budget_category_id"), "monthly_budget", ["category_id"], unique=False)
    op.create_index(op.f("ix_monthly_budget_year"), "monthly_budget", ["year"], unique=False)
    op.create_index(op.f("ix_monthly_budget_month"), "monthly_budget", ["month"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_monthly_budget_month"), table_name="monthly_budget")
    op.drop_index(op.f("ix_monthly_budget_year"), table_name="monthly_budget")
    op.drop_index(op.f("ix_monthly_budget_category_id"), table_name="monthly_budget")
    op.drop_index(op.f("ix_monthly_budget_user_id"), table_name="monthly_budget")
    op.drop_table("monthly_budget")
