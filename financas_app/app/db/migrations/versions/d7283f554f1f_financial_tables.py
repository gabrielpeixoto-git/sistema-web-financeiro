"""financial tables

Revision ID: d7283f554f1f
Revises: 95786821c177
Create Date: 2026-04-15 17:58:46.683849
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes



revision = 'd7283f554f1f'
down_revision = '95786821c177'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("currency", sqlmodel.sql.sqltypes.AutoString(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_account_user_id"), "account", ["user_id"], unique=False)

    op.create_table(
        "category",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_category_user_id"), "category", ["user_id"], unique=False)

    op.create_table(
        "transaction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("kind", sqlmodel.sql.sqltypes.AutoString(length=8), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["account.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_transaction_account_id"), "transaction", ["account_id"], unique=False)
    op.create_index(op.f("ix_transaction_category_id"), "transaction", ["category_id"], unique=False)
    op.create_index(op.f("ix_transaction_occurred_on"), "transaction", ["occurred_on"], unique=False)
    op.create_index(op.f("ix_transaction_user_id"), "transaction", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_transaction_user_id"), table_name="transaction")
    op.drop_index(op.f("ix_transaction_occurred_on"), table_name="transaction")
    op.drop_index(op.f("ix_transaction_category_id"), table_name="transaction")
    op.drop_index(op.f("ix_transaction_account_id"), table_name="transaction")
    op.drop_table("transaction")
    op.drop_index(op.f("ix_category_user_id"), table_name="category")
    op.drop_table("category")
    op.drop_index(op.f("ix_account_user_id"), table_name="account")
    op.drop_table("account")

