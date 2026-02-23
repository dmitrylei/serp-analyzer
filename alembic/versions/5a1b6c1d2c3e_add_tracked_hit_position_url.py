"""add tracked hit position and url

Revision ID: 5a1b6c1d2c3e
Revises: 2b6f0a8c8d51
Create Date: 2026-02-22 22:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "5a1b6c1d2c3e"
down_revision = "2b6f0a8c8d51"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tracked_hits", sa.Column("position", sa.Integer(), nullable=True))
    op.add_column("tracked_hits", sa.Column("url", sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column("tracked_hits", "url")
    op.drop_column("tracked_hits", "position")
