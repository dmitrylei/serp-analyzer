"""add keyword language

Revision ID: 7a2d1c3b0b2a
Revises: 5c6c010cb60c
Create Date: 2026-02-22 19:36:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7a2d1c3b0b2a"
down_revision = "5c6c010cb60c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("keywords", sa.Column("language", sa.String(length=8), nullable=True))
    op.create_index(op.f("ix_keywords_language"), "keywords", ["language"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_keywords_language"), table_name="keywords")
    op.drop_column("keywords", "language")
