"""add canonical tracking

Revision ID: 8f6e1b2c7d9a
Revises: 5a1b6c1d2c3e
Create Date: 2026-02-25 22:55:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "8f6e1b2c7d9a"
down_revision = "5a1b6c1d2c3e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "canonical_sites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index(op.f("ix_canonical_sites_url"), "canonical_sites", ["url"], unique=True)

    op.create_table(
        "canonical_edges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("canonical_url", sa.String(length=1000), nullable=True),
        sa.Column("canonical_google", sa.String(length=1000), nullable=True),
        sa.Column("canonical_bot", sa.String(length=1000), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_canonical_edges_run_id"), "canonical_edges", ["run_id"], unique=False)
    op.create_index(op.f("ix_canonical_edges_source_url"), "canonical_edges", ["source_url"], unique=False)

    op.create_table(
        "canonical_favorites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index(op.f("ix_canonical_favorites_url"), "canonical_favorites", ["url"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_canonical_favorites_url"), table_name="canonical_favorites")
    op.drop_table("canonical_favorites")
    op.drop_index(op.f("ix_canonical_edges_source_url"), table_name="canonical_edges")
    op.drop_index(op.f("ix_canonical_edges_run_id"), table_name="canonical_edges")
    op.drop_table("canonical_edges")
    op.drop_index(op.f("ix_canonical_sites_url"), table_name="canonical_sites")
    op.drop_table("canonical_sites")
