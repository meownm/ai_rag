"""add ann index for chunk_vectors embedding retrieval

Revision ID: 0004_add_chunk_vectors_ann_index
Revises: 0003_add_cross_links_table
Create Date: 2026-02-11 02:00:00.000000
"""

from alembic import op


revision = "0004_add_chunk_vectors_ann_index"
down_revision = "0003_add_cross_links_table"
branch_labels = None
depends_on = None


INDEX_NAME = "ix_chunk_vectors_embedding_ann"


def upgrade() -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
                IF EXISTS (SELECT 1 FROM pg_am WHERE amname = 'hnsw') THEN
                    EXECUTE 'CREATE INDEX IF NOT EXISTS {INDEX_NAME} ON chunk_vectors USING hnsw (embedding vector_l2_ops)';
                ELSIF EXISTS (SELECT 1 FROM pg_am WHERE amname = 'ivfflat') THEN
                    EXECUTE 'CREATE INDEX IF NOT EXISTS {INDEX_NAME} ON chunk_vectors USING ivfflat (embedding vector_l2_ops) WITH (lists = 100)';
                END IF;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
