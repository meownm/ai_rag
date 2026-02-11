"""add cross_links table for confluence graph

Revision ID: 0003_add_cross_links_table
Revises: 0002_chunk_fts_upgrade
Create Date: 2026-02-11 00:20:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_add_cross_links_table"
down_revision = "0002_chunk_fts_upgrade"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cross_links",
        sa.Column("from_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.document_id"), primary_key=True),
        sa.Column("to_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.document_id"), nullable=True),
        sa.Column("link_url", sa.String(2048), primary_key=True),
        sa.Column("link_type", sa.Enum("CONFLUENCE_PAGE_LINK", "EXTERNAL_URL", "ATTACHMENT_LINK", name="link_type"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("cross_links")
