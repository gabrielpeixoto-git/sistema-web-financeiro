"""recurring rules + transaction.recurring_rule_id

Revision ID: d6a0c3f2b4e5
Revises: c5f9b2e1a3d4
Create Date: 2026-04-15 22:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision = "d6a0c3f2b4e5"
down_revision = "c5f9b2e1a3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()
    if "recurringrule" not in tables:
        op.create_table(
            "recurringrule",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("account_id", sa.Integer(), nullable=False),
            sa.Column("category_id", sa.Integer(), nullable=True),
            sa.Column("kind", sqlmodel.sql.sqltypes.AutoString(length=8), nullable=False),
            sa.Column("amount_cents", sa.Integer(), nullable=False),
            sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
            sa.Column("frequency", sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
            sa.Column("next_due", sa.Date(), nullable=False),
            sa.Column("end_on", sa.Date(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["account_id"], ["account.id"]),
            sa.ForeignKeyConstraint(["category_id"], ["category.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_recurringrule_user_id"), "recurringrule", ["user_id"], unique=False)
        op.create_index(op.f("ix_recurringrule_account_id"), "recurringrule", ["account_id"], unique=False)
        op.create_index(op.f("ix_recurringrule_category_id"), "recurringrule", ["category_id"], unique=False)
        op.create_index(op.f("ix_recurringrule_next_due"), "recurringrule", ["next_due"], unique=False)

    cols = [c["name"] for c in insp.get_columns("transaction")]
    if "recurring_rule_id" not in cols:
        op.add_column(
            "transaction",
            sa.Column("recurring_rule_id", sa.Integer(), nullable=True),
        )
        op.create_index(
            op.f("ix_transaction_recurring_rule_id"),
            "transaction",
            ["recurring_rule_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_transaction_recurring_rule_id"), table_name="transaction")
    op.drop_column("transaction", "recurring_rule_id")
    op.drop_index(op.f("ix_recurringrule_next_due"), table_name="recurringrule")
    op.drop_index(op.f("ix_recurringrule_category_id"), table_name="recurringrule")
    op.drop_index(op.f("ix_recurringrule_account_id"), table_name="recurringrule")
    op.drop_index(op.f("ix_recurringrule_user_id"), table_name="recurringrule")
    op.drop_table("recurringrule")
