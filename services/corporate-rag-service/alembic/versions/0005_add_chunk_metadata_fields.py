"""add chunk metadata fields for chunking spec v1

Revision ID: 0005_add_chunk_metadata_fields
Revises: 0004_add_chunk_vectors_ann_index
Create Date: 2026-02-11
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0005_add_chunk_metadata_fields"
down_revision = "0004_add_chunk_vectors_ann_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("chunk_type", sa.String(length=32), nullable=True))
    op.add_column("chunks", sa.Column("char_start", sa.Integer(), nullable=True))
    op.add_column("chunks", sa.Column("char_end", sa.Integer(), nullable=True))
    op.add_column("chunks", sa.Column("block_start_idx", sa.Integer(), nullable=True))
    op.add_column("chunks", sa.Column("block_end_idx", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("chunks", "block_end_idx")
    op.drop_column("chunks", "block_start_idx")
    op.drop_column("chunks", "char_end")
    op.drop_column("chunks", "char_start")
    op.drop_column("chunks", "chunk_type")
