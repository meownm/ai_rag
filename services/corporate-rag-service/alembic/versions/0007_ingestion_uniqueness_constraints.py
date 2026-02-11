"""add ingestion uniqueness constraints

Revision ID: 0007_ingestion_uniqueness_constraints
Revises: 0006_add_conversation_memory_tables
Create Date: 2026-02-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_ingestion_uniqueness_constraints"
down_revision = "0006_add_conversation_memory_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_sources_tenant_type_external_ref",
        "sources",
        ["tenant_id", "source_type", "external_ref"],
    )
    op.create_unique_constraint(
        "uq_source_versions_source_checksum",
        "source_versions",
        ["source_id", "checksum"],
    )
    op.create_index("ix_source_versions_source_id", "source_versions", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_source_versions_source_id", table_name="source_versions")
    op.drop_constraint("uq_source_versions_source_checksum", "source_versions", type_="unique")
    op.drop_constraint("uq_sources_tenant_type_external_ref", "sources", type_="unique")
