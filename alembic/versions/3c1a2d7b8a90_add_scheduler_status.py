"""add scheduler status

Revision ID: 3c1a2d7b8a90
Revises: 9f7f2f1c1a10
Create Date: 2026-02-22 20:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "3c1a2d7b8a90"
down_revision = "9f7f2f1c1a10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduler_status",
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("running", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )


def downgrade() -> None:
    op.drop_table("scheduler_status")
