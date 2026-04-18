"""password reset token table

Revision ID: b4e8a1c2d3f4
Revises: daef646fda44
Create Date: 2026-04-15 20:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision = "b4e8a1c2d3f4"
down_revision = "daef646fda44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "passwordresettoken" in insp.get_table_names():
        return
    op.create_table(
        "passwordresettoken",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_passwordresettoken_token_hash"),
        "passwordresettoken",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_passwordresettoken_user_id"),
        "passwordresettoken",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_passwordresettoken_user_id"), table_name="passwordresettoken")
    op.drop_index(op.f("ix_passwordresettoken_token_hash"), table_name="passwordresettoken")
    op.drop_table("passwordresettoken")
