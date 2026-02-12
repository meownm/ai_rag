"""chunk_vectors upsert schema alignment

Revision ID: 0015_chunk_vectors_upsert_schema_alignment
Revises: 0014_chunk_vectors_updated_at_integrity_guard
Create Date: 2026-02-12 16:20:00.000000
"""

from alembic import op


revision = "0015_chunk_vectors_upsert_schema_alignment"
down_revision = "0014_chunk_vectors_updated_at_integrity_guard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'chunk_vectors'
                  AND column_name = 'updated_at'
            ) THEN
                ALTER TABLE chunk_vectors
                ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now();
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            ALTER TABLE chunk_vectors
            ALTER COLUMN updated_at SET DEFAULT now(),
            ALTER COLUMN updated_at SET NOT NULL;
        END
        $$;
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_chunk_vectors_tenant_chunk
        ON chunk_vectors (tenant_id, chunk_id)
        """
    )


def downgrade() -> None:
    # Non-destructive guard migration.
    pass
