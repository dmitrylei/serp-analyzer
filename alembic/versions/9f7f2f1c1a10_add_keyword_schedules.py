"""add keyword schedules

Revision ID: 9f7f2f1c1a10
Revises: 7a2d1c3b0b2a
Create Date: 2026-02-22 20:15:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "9f7f2f1c1a10"
down_revision = "7a2d1c3b0b2a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "keyword_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("keyword_id", sa.Integer(), nullable=False),
        sa.Column("interval_hours", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["keyword_id"], ["keywords.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_keyword_schedules_keyword_id"), "keyword_schedules", ["keyword_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_keyword_schedules_keyword_id"), table_name="keyword_schedules")
    op.drop_table("keyword_schedules")
