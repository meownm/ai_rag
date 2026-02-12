"""enforce unique document per tenant/source_version

Revision ID: 0012_documents_unique_tenant_source_version
Revises: 0011_add_chunk_vectors_updated_at
Create Date: 2026-02-12 00:20:00.000000
"""

from alembic import op


revision = "0012_documents_unique_tenant_source_version"
down_revision = "0011_add_chunk_vectors_updated_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked AS (
            SELECT
                document_id,
                tenant_id,
                source_version_id,
                ROW_NUMBER() OVER (
                    PARTITION BY tenant_id, source_version_id
                    ORDER BY updated_date DESC NULLS LAST, document_id
                ) AS rn,
                FIRST_VALUE(document_id) OVER (
                    PARTITION BY tenant_id, source_version_id
                    ORDER BY updated_date DESC NULLS LAST, document_id
                ) AS keep_document_id
            FROM documents
            WHERE source_version_id IS NOT NULL
        ), duplicates AS (
            SELECT document_id, keep_document_id
            FROM ranked
            WHERE rn > 1
        )
        UPDATE chunks c
        SET document_id = d.keep_document_id
        FROM duplicates d
        WHERE c.document_id = d.document_id
        """
    )

    op.execute(
        """
        WITH ranked AS (
            SELECT
                document_id,
                tenant_id,
                source_version_id,
                ROW_NUMBER() OVER (
                    PARTITION BY tenant_id, source_version_id
                    ORDER BY updated_date DESC NULLS LAST, document_id
                ) AS rn,
                FIRST_VALUE(document_id) OVER (
                    PARTITION BY tenant_id, source_version_id
                    ORDER BY updated_date DESC NULLS LAST, document_id
                ) AS keep_document_id
            FROM documents
            WHERE source_version_id IS NOT NULL
        ), duplicates AS (
            SELECT document_id, keep_document_id
            FROM ranked
            WHERE rn > 1
        )
        UPDATE document_links dl
        SET from_document_id = d.keep_document_id
        FROM duplicates d
        WHERE dl.from_document_id = d.document_id
        """
    )

    op.execute(
        """
        WITH ranked AS (
            SELECT
                document_id,
                tenant_id,
                source_version_id,
                ROW_NUMBER() OVER (
                    PARTITION BY tenant_id, source_version_id
                    ORDER BY updated_date DESC NULLS LAST, document_id
                ) AS rn,
                FIRST_VALUE(document_id) OVER (
                    PARTITION BY tenant_id, source_version_id
                    ORDER BY updated_date DESC NULLS LAST, document_id
                ) AS keep_document_id
            FROM documents
            WHERE source_version_id IS NOT NULL
        ), duplicates AS (
            SELECT document_id, keep_document_id
            FROM ranked
            WHERE rn > 1
        )
        UPDATE document_links dl
        SET to_document_id = d.keep_document_id
        FROM duplicates d
        WHERE dl.to_document_id = d.document_id
        """
    )

    op.execute(
        """
        WITH ranked AS (
            SELECT
                document_id,
                tenant_id,
                source_version_id,
                ROW_NUMBER() OVER (
                    PARTITION BY tenant_id, source_version_id
                    ORDER BY updated_date DESC NULLS LAST, document_id
                ) AS rn,
                FIRST_VALUE(document_id) OVER (
                    PARTITION BY tenant_id, source_version_id
                    ORDER BY updated_date DESC NULLS LAST, document_id
                ) AS keep_document_id
            FROM documents
            WHERE source_version_id IS NOT NULL
        ), duplicates AS (
            SELECT document_id, keep_document_id
            FROM ranked
            WHERE rn > 1
        )
        UPDATE cross_links cl
        SET from_document_id = d.keep_document_id
        FROM duplicates d
        WHERE cl.from_document_id = d.document_id
        """
    )

    op.execute(
        """
        WITH ranked AS (
            SELECT
                document_id,
                tenant_id,
                source_version_id,
                ROW_NUMBER() OVER (
                    PARTITION BY tenant_id, source_version_id
                    ORDER BY updated_date DESC NULLS LAST, document_id
                ) AS rn,
                FIRST_VALUE(document_id) OVER (
                    PARTITION BY tenant_id, source_version_id
                    ORDER BY updated_date DESC NULLS LAST, document_id
                ) AS keep_document_id
            FROM documents
            WHERE source_version_id IS NOT NULL
        ), duplicates AS (
            SELECT document_id, keep_document_id
            FROM ranked
            WHERE rn > 1
        )
        UPDATE cross_links cl
        SET to_document_id = d.keep_document_id
        FROM duplicates d
        WHERE cl.to_document_id = d.document_id
        """
    )

    op.execute(
        """
        WITH ranked AS (
            SELECT
                document_id,
                tenant_id,
                source_version_id,
                ROW_NUMBER() OVER (
                    PARTITION BY tenant_id, source_version_id
                    ORDER BY updated_date DESC NULLS LAST, document_id
                ) AS rn
            FROM documents
            WHERE source_version_id IS NOT NULL
        )
        DELETE FROM documents d
        USING ranked r
        WHERE d.document_id = r.document_id
          AND r.rn > 1
        """
    )

    op.create_unique_constraint(
        "uq_documents_tenant_source_version",
        "documents",
        ["tenant_id", "source_version_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_documents_tenant_source_version", "documents", type_="unique")
