"""add conversation memory tables

Revision ID: 0006_add_conversation_memory_tables
Revises: 0005_add_chunk_metadata_fields
Create Date: 2026-02-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0006_add_conversation_memory_tables"
down_revision = "0005_add_chunk_metadata_fields"
branch_labels = None
depends_on = None


conversation_status = sa.Enum("active", "archived", name="conversation_status")
conversation_role = sa.Enum("user", "assistant", "system", name="conversation_role")
rewrite_strategy = sa.Enum("none", "llm_rewrite", name="rewrite_strategy")


def upgrade() -> None:
    bind = op.get_bind()
    conversation_status.create(bind, checkfirst=True)
    conversation_role.create(bind, checkfirst=True)
    rewrite_strategy.create(bind, checkfirst=True)

    op.create_table(
        "conversations",
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", conversation_status, nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_conversations_tenant_id", "conversations", ["tenant_id"])

    op.create_table(
        "conversation_turns",
        sa.Column("turn_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.conversation_id"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("role", conversation_role, nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.UniqueConstraint("conversation_id", "turn_index", name="uq_conversation_turns_conversation_turn_index"),
    )
    op.create_index("ix_conversation_turns_tenant_id", "conversation_turns", ["tenant_id"])
    op.create_index("ix_conversation_turns_conversation_id", "conversation_turns", ["conversation_id"])

    op.create_table(
        "query_resolutions",
        sa.Column("resolution_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turn_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversation_turns.turn_id"), nullable=False),
        sa.Column("resolved_query_text", sa.Text(), nullable=False),
        sa.Column("rewrite_strategy", rewrite_strategy, nullable=False, server_default="none"),
        sa.Column("rewrite_inputs", postgresql.JSONB(), nullable=True),
        sa.Column("rewrite_confidence", sa.Float(), nullable=True),
        sa.Column("topic_shift_detected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("needs_clarification", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("clarification_question", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_query_resolutions_tenant_id", "query_resolutions", ["tenant_id"])
    op.create_index("ix_query_resolutions_conversation_id", "query_resolutions", ["conversation_id"])
    op.create_index("ix_query_resolutions_turn_id", "query_resolutions", ["turn_id"])

    op.create_table(
        "retrieval_trace_items",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turn_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("score_lex_raw", sa.Float(), nullable=True),
        sa.Column("score_vec_raw", sa.Float(), nullable=True),
        sa.Column("score_rerank_raw", sa.Float(), nullable=True),
        sa.Column("score_final", sa.Float(), nullable=True),
        sa.Column("used_in_context", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("used_in_answer", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("citation_rank", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("tenant_id", "conversation_id", "turn_id", "document_id", "chunk_id", "ordinal", name="pk_retrieval_trace_items"),
    )
    op.create_index("ix_retrieval_trace_items_tenant_conv_turn", "retrieval_trace_items", ["tenant_id", "conversation_id", "turn_id"])
    op.create_index("ix_retrieval_trace_items_tenant_conv_created", "retrieval_trace_items", ["tenant_id", "conversation_id", "created_at"])

    op.create_table(
        "conversation_summaries",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary_version", sa.Integer(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("covers_turn_index_to", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("tenant_id", "conversation_id", "summary_version", name="pk_conversation_summaries"),
        sa.UniqueConstraint("tenant_id", "conversation_id", "summary_version", name="uq_conversation_summaries_tenant_conversation_version"),
    )


def downgrade() -> None:
    op.drop_table("conversation_summaries")
    op.drop_index("ix_retrieval_trace_items_tenant_conv_created", table_name="retrieval_trace_items")
    op.drop_index("ix_retrieval_trace_items_tenant_conv_turn", table_name="retrieval_trace_items")
    op.drop_table("retrieval_trace_items")
    op.drop_index("ix_query_resolutions_turn_id", table_name="query_resolutions")
    op.drop_index("ix_query_resolutions_conversation_id", table_name="query_resolutions")
    op.drop_index("ix_query_resolutions_tenant_id", table_name="query_resolutions")
    op.drop_table("query_resolutions")
    op.drop_index("ix_conversation_turns_conversation_id", table_name="conversation_turns")
    op.drop_index("ix_conversation_turns_tenant_id", table_name="conversation_turns")
    op.drop_table("conversation_turns")
    op.drop_index("ix_conversations_tenant_id", table_name="conversations")
    op.drop_table("conversations")

    bind = op.get_bind()
    rewrite_strategy.drop(bind, checkfirst=True)
    conversation_role.drop(bind, checkfirst=True)
    conversation_status.drop(bind, checkfirst=True)
