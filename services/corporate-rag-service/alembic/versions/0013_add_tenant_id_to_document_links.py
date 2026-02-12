"""add tenant_id to document_links

Revision ID: 0013_add_tenant_id_to_document_links
Revises: 0012_documents_unique_tenant_source_version
Create Date: 2026-02-12 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0013_add_tenant_id_to_document_links"
down_revision = "0012_documents_unique_tenant_source_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_links", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        """
        UPDATE document_links dl
        SET tenant_id = d.tenant_id
        FROM documents d
        WHERE d.document_id = dl.from_document_id
        """
    )
    op.alter_column("document_links", "tenant_id", nullable=False)
    op.create_index("ix_document_links_tenant_id", "document_links", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_document_links_tenant_id", table_name="document_links")
    op.drop_column("document_links", "tenant_id")
