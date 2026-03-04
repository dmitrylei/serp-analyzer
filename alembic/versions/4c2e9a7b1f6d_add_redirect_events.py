"""add redirect events

Revision ID: 4c2e9a7b1f6d
Revises: 8f6e1b2c7d9a
Create Date: 2026-02-26 00:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "4c2e9a7b1f6d"
down_revision = "8f6e1b2c7d9a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "redirect_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("final_url", sa.String(length=1000), nullable=False),
        sa.Column("source_domain", sa.String(length=255), nullable=False),
        sa.Column("final_domain", sa.String(length=255), nullable=False),
        sa.Column("chain", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_redirect_events_run_id"), "redirect_events", ["run_id"], unique=False)
    op.create_index(op.f("ix_redirect_events_source_domain"), "redirect_events", ["source_domain"], unique=False)
    op.create_index(op.f("ix_redirect_events_final_domain"), "redirect_events", ["final_domain"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_redirect_events_final_domain"), table_name="redirect_events")
    op.drop_index(op.f("ix_redirect_events_source_domain"), table_name="redirect_events")
    op.drop_index(op.f("ix_redirect_events_run_id"), table_name="redirect_events")
    op.drop_table("redirect_events")
