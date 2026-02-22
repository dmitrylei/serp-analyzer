"""add tracked sites and hits

Revision ID: 2b6f0a8c8d51
Revises: 3c1a2d7b8a90
Create Date: 2026-02-22 21:05:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "2b6f0a8c8d51"
down_revision = "3c1a2d7b8a90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tracked_sites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain"),
    )
    op.create_index(op.f("ix_tracked_sites_domain"), "tracked_sites", ["domain"], unique=True)

    op.create_table(
        "tracked_hits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tracked_site_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("keyword_id", sa.Integer(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tracked_site_id"], ["tracked_sites.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.ForeignKeyConstraint(["keyword_id"], ["keywords.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tracked_hits_tracked_site_id"), "tracked_hits", ["tracked_site_id"], unique=False)
    op.create_index(op.f("ix_tracked_hits_run_id"), "tracked_hits", ["run_id"], unique=False)
    op.create_index(op.f("ix_tracked_hits_keyword_id"), "tracked_hits", ["keyword_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tracked_hits_keyword_id"), table_name="tracked_hits")
    op.drop_index(op.f("ix_tracked_hits_run_id"), table_name="tracked_hits")
    op.drop_index(op.f("ix_tracked_hits_tracked_site_id"), table_name="tracked_hits")
    op.drop_table("tracked_hits")
    op.drop_index(op.f("ix_tracked_sites_domain"), table_name="tracked_sites")
    op.drop_table("tracked_sites")
