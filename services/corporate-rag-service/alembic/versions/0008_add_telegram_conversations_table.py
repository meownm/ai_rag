"""add telegram conversations table

Revision ID: 0008_add_telegram_conversations_table
Revises: 0007_ingestion_uniqueness_constraints
Create Date: 2026-02-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_add_telegram_conversations_table"
down_revision = "0007_ingestion_uniqueness_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_conversations",
        sa.Column("user_id", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("clarification_depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("debug_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_question", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_telegram_conversations_updated_at", "telegram_conversations", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_telegram_conversations_updated_at", table_name="telegram_conversations")
    op.drop_table("telegram_conversations")
