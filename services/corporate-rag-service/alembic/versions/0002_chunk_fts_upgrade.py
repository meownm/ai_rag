"""upgrade chunk_fts for fts lexical retrieval

Revision ID: 0002_chunk_fts_upgrade
Revises: 0001_initial
Create Date: 2026-02-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_chunk_fts_upgrade"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chunk_fts",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.drop_constraint("chunk_fts_pkey", "chunk_fts", type_="primary")
    op.create_primary_key("pk_chunk_fts", "chunk_fts", ["tenant_id", "chunk_id"])
    op.create_index("ix_chunk_fts_fts_doc", "chunk_fts", ["fts_doc"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_chunk_fts_fts_doc", table_name="chunk_fts")
    op.drop_constraint("pk_chunk_fts", "chunk_fts", type_="primary")
    op.create_primary_key("chunk_fts_pkey", "chunk_fts", ["chunk_id"])
    op.drop_column("chunk_fts", "updated_at")
