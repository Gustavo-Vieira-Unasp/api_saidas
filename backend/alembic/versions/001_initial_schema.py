"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ra", sa.String(length=64), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("unasp_username", sa.String(length=255), nullable=True),
        sa.Column("unasp_password_enc", sa.String(length=512), nullable=True),
        sa.Column("unasp_profile", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_ra"), "users", ["ra"], unique=True)

    op.create_table(
        "templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_templates_user_id"), "templates", ["user_id"])

    op.create_table(
        "schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("trigger_type", sa.String(length=16), nullable=False),
        sa.Column("run_at", sa.DateTime(), nullable=True),
        sa.Column("hour", sa.Integer(), nullable=True),
        sa.Column("minute", sa.Integer(), nullable=True),
        sa.Column("cron", sa.String(length=64), nullable=True),
        sa.Column("date_strategy", sa.String(length=16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_schedules_user_id"), "schedules", ["user_id"])

    op.create_table(
        "exit_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("schedule_id", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("screenshot_path", sa.String(length=512), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["schedule_id"], ["schedules.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_exit_requests_user_id"), "exit_requests", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_exit_requests_user_id"), table_name="exit_requests")
    op.drop_table("exit_requests")
    op.drop_index(op.f("ix_schedules_user_id"), table_name="schedules")
    op.drop_table("schedules")
    op.drop_index(op.f("ix_templates_user_id"), table_name="templates")
    op.drop_table("templates")
    op.drop_index(op.f("ix_users_ra"), table_name="users")
    op.drop_table("users")
