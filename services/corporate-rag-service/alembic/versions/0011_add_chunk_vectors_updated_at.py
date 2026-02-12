"""add updated_at to chunk_vectors

Revision ID: 0011_add_chunk_vectors_updated_at
Revises: 0010_create_source_sync_state
Create Date: 2026-02-12 00:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_add_chunk_vectors_updated_at"
down_revision = "0010_create_source_sync_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chunk_vectors",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_column("chunk_vectors", "updated_at")
