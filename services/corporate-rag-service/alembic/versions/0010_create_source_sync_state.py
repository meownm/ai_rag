"""create source_sync_state table

Revision ID: 0010_create_source_sync_state
Revises: 0009_async_jobs_file_upload_and_embedding_mode
Create Date: 2026-02-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_create_source_sync_state"
down_revision = "0009_async_jobs_file_upload_and_embedding_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_sync_state",
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("external_ref", sa.Text(), nullable=False),
        sa.Column("last_seen_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_checksum", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.Text(), nullable=False, server_default="never"),
        sa.Column("last_error_code", sa.Text(), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("tenant_id", "source_type", "external_ref", name="pk_source_sync_state"),
    )
    op.create_index("ix_source_sync_state_tenant_type_synced", "source_sync_state", ["tenant_id", "source_type", "last_synced_at"])
    op.create_index("ix_source_sync_state_tenant_type_status", "source_sync_state", ["tenant_id", "source_type", "last_status"])


def downgrade() -> None:
    op.drop_index("ix_source_sync_state_tenant_type_status", table_name="source_sync_state")
    op.drop_index("ix_source_sync_state_tenant_type_synced", table_name="source_sync_state")
    op.drop_table("source_sync_state")
