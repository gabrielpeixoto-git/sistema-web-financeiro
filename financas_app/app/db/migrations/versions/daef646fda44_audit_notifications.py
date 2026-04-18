"""audit notifications

Revision ID: daef646fda44
Revises: d7283f554f1f
Create Date: 2026-04-15 19:03:42.806481
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes



revision = 'daef646fda44'
down_revision = 'd7283f554f1f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auditlog",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("entity", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("detail", sqlmodel.sql.sqltypes.AutoString(length=400), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auditlog_action"), "auditlog", ["action"], unique=False)
    op.create_index(op.f("ix_auditlog_created_at"), "auditlog", ["created_at"], unique=False)
    op.create_index(op.f("ix_auditlog_entity_id"), "auditlog", ["entity_id"], unique=False)
    op.create_index(op.f("ix_auditlog_user_id"), "auditlog", ["user_id"], unique=False)

    op.create_table(
        "notification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("kind", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column("message", sqlmodel.sql.sqltypes.AutoString(length=400), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_created_at"), "notification", ["created_at"], unique=False)
    op.create_index(op.f("ix_notification_kind"), "notification", ["kind"], unique=False)
    op.create_index(op.f("ix_notification_user_id"), "notification", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_user_id"), table_name="notification")
    op.drop_index(op.f("ix_notification_kind"), table_name="notification")
    op.drop_index(op.f("ix_notification_created_at"), table_name="notification")
    op.drop_table("notification")
    op.drop_index(op.f("ix_auditlog_user_id"), table_name="auditlog")
    op.drop_index(op.f("ix_auditlog_entity_id"), table_name="auditlog")
    op.drop_index(op.f("ix_auditlog_created_at"), table_name="auditlog")
    op.drop_index(op.f("ix_auditlog_action"), table_name="auditlog")
    op.drop_table("auditlog")

