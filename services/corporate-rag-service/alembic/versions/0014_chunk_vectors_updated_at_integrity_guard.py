"""chunk_vectors updated_at integrity guard

Revision ID: 0014_chunk_vectors_updated_at_integrity_guard
Revises: 0013_add_tenant_id_to_document_links
Create Date: 2026-02-12 14:40:00.000000
"""

from alembic import op


revision = "0014_chunk_vectors_updated_at_integrity_guard"
down_revision = "0013_add_tenant_id_to_document_links"
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


def downgrade() -> None:
    # backward-compatible guard migration; no destructive downgrade.
    pass
