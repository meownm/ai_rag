"""async jobs and file upload metadata

Revision ID: 0009
Revises: 0008
"""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'FILE_UPLOAD_OBJECT'")
    op.add_column("ingest_jobs", sa.Column("job_payload_json", sa.JSON(), nullable=True))
    op.add_column("ingest_jobs", sa.Column("result_json", sa.JSON(), nullable=True))
    op.add_column("chunk_vectors", sa.Column("embedding_input_mode", sa.String(length=32), nullable=False, server_default="path_text_v1"))


def downgrade() -> None:
    op.drop_column("chunk_vectors", "embedding_input_mode")
    op.drop_column("ingest_jobs", "result_json")
    op.drop_column("ingest_jobs", "job_payload_json")
