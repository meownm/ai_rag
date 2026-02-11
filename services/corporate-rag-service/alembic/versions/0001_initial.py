"""initial schema

Revision ID: 0001
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    source_type = sa.Enum("CONFLUENCE_PAGE", "CONFLUENCE_ATTACHMENT", "FILE_CATALOG_OBJECT", name="source_type")
    source_status = sa.Enum("DISCOVERED", "FETCHED", "NORMALIZED", "INDEXED", "FAILED", name="source_status")
    tenant_role = sa.Enum("TENANT_ADMIN", "TENANT_EDITOR", "TENANT_VIEWER", name="tenant_role")
    citations_mode = sa.Enum("DISABLED", "OPTIONAL", "REQUIRED", name="citations_mode")
    only_sources_mode = sa.Enum("STRICT", name="only_sources_mode")
    job_type = sa.Enum("SYNC_CONFLUENCE", "SYNC_FILE_CATALOG", "PREPROCESS", "INDEX_LEXICAL", "INDEX_VECTOR", "REINDEX_ALL", name="job_type")
    job_status = sa.Enum("queued", "processing", "retrying", "done", "error", "canceled", "expired", name="job_status")
    link_type = sa.Enum("CONFLUENCE_PAGE_LINK", "EXTERNAL_URL", "ATTACHMENT_LINK", name="link_type")
    pipeline_stage = sa.Enum(
        "INGEST_DISCOVERY", "INGEST_FETCH", "NORMALIZE_MARKDOWN", "STRUCTURE_PARSE", "CHUNK_LOGICAL",
        "INDEX_BM25", "EMBED_REQUEST", "INDEX_VECTOR", "SEARCH_LEXICAL", "SEARCH_VECTOR", "FUSION_BOOST",
        "RERANK", "ANSWER_COMPOSE", "ANSWER_VALIDATE_ONLY_SOURCES",
        name="pipeline_stage",
    )
    pipeline_stage_status = sa.Enum("STARTED", "COMPLETED", "FAILED", "SKIPPED", name="pipeline_stage_status")
    event_type = sa.Enum("API_REQUEST", "API_RESPONSE", "EMBEDDINGS_REQUEST", "EMBEDDINGS_RESPONSE", "LLM_REQUEST", "LLM_RESPONSE", "PIPELINE_STAGE", "ERROR", name="event_type")
    log_data_mode = sa.Enum("PLAIN", "MASKED", "HASHED", name="log_data_mode")
    only_sources_verdict = sa.Enum("PASS", "FAIL", name="only_sources_verdict")

    op.create_table(
        "tenants",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_key", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "tenant_settings",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.tenant_id"), primary_key=True),
        sa.Column("citations_mode", citations_mode, nullable=False),
        sa.Column("only_sources_mode", only_sources_mode, nullable=False),
        sa.Column("default_prompt_template", sa.Text(), nullable=True),
        sa.Column("metadata_boost_profile", postgresql.JSONB(), nullable=True),
        sa.Column("link_boost_profile", postgresql.JSONB(), nullable=True),
    )

    op.create_table("local_groups", sa.Column("group_id", sa.Integer(), primary_key=True), sa.Column("group_name", sa.String(255), nullable=False, unique=True))
    op.create_table(
        "tenant_group_bindings",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.tenant_id"), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("local_groups.group_id"), primary_key=True),
        sa.Column("role", tenant_role, nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("principal_name", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
    )
    op.create_table(
        "user_group_memberships",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("local_groups.group_id"), primary_key=True),
    )

    op.create_table(
        "sources",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("external_ref", sa.String(1024), nullable=False),
        sa.Column("status", source_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_sources_tenant_id", "sources", ["tenant_id"])

    op.create_table(
        "source_versions",
        sa.Column("source_version_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.source_id"), nullable=False),
        sa.Column("version_label", sa.String(255), nullable=False),
        sa.Column("checksum", sa.String(255), nullable=False),
        sa.Column("s3_raw_uri", sa.String(1024), nullable=False),
        sa.Column("s3_markdown_uri", sa.String(1024), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "documents",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.source_id"), nullable=True),
        sa.Column("source_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("source_versions.source_version_id"), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("created_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("space_key", sa.String(128), nullable=True),
        sa.Column("page_id", sa.String(128), nullable=True),
        sa.Column("parent_id", sa.String(128), nullable=True),
        sa.Column("url", sa.String(2048), nullable=True),
        sa.Column("labels", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"])

    op.create_table(
        "document_links",
        sa.Column("from_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.document_id"), primary_key=True),
        sa.Column("to_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.document_id"), nullable=True),
        sa.Column("link_url", sa.String(2048), primary_key=True),
        sa.Column("link_type", link_type, nullable=False),
    )

    op.create_table(
        "chunks",
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.document_id"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("chunk_path", sa.String(1024), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
    )
    op.create_index("ix_chunks_tenant_id", "chunks", ["tenant_id"])

    op.create_table(
        "chunk_fts",
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chunks.chunk_id"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("fts_doc", postgresql.TSVECTOR(), nullable=False),
    )

    op.execute(
        """
        CREATE TABLE chunk_vectors (
            chunk_id uuid PRIMARY KEY REFERENCES chunks(chunk_id),
            tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
            embedding_model varchar(255) NOT NULL,
            embedding vector(1024) NOT NULL,
            embedding_dim integer NOT NULL
        )
        """
    )
    op.create_index("ix_chunk_vectors_tenant_id", "chunk_vectors", ["tenant_id"])

    op.create_table(
        "ingest_jobs",
        sa.Column("job_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("job_type", job_type, nullable=False),
        sa.Column("job_status", job_status, nullable=False),
        sa.Column("requested_by", sa.String(255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_ingest_jobs_tenant_id", "ingest_jobs", ["tenant_id"])

    op.create_table(
        "search_requests",
        sa.Column("search_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("citations_requested", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "search_candidates",
        sa.Column("search_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("search_requests.search_id"), primary_key=True),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chunks.chunk_id"), primary_key=True),
        sa.Column("lex_score", sa.Float(), nullable=False),
        sa.Column("vec_score", sa.Float(), nullable=False),
        sa.Column("rerank_score", sa.Float(), nullable=False),
        sa.Column("boosts_json", postgresql.JSONB(), nullable=False),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column("rank_position", sa.Integer(), nullable=False),
    )

    op.create_table(
        "answers",
        sa.Column("answer_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("search_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("search_requests.search_id"), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("only_sources_verdict", only_sources_verdict, nullable=False),
        sa.Column("citations_json", postgresql.JSONB(), nullable=True),
    )

    op.create_table(
        "pipeline_trace",
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("stage", pipeline_stage, nullable=False),
        sa.Column("status", pipeline_stage_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(), nullable=False),
    )

    op.create_table(
        "event_logs",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", event_type, nullable=False),
        sa.Column("log_data_mode", log_data_mode, nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("event_logs")
    op.drop_table("pipeline_trace")
    op.drop_table("answers")
    op.drop_table("search_candidates")
    op.drop_table("search_requests")
    op.drop_index("ix_ingest_jobs_tenant_id", table_name="ingest_jobs")
    op.drop_table("ingest_jobs")
    op.drop_index("ix_chunk_vectors_tenant_id", table_name="chunk_vectors")
    op.drop_table("chunk_vectors")
    op.drop_table("chunk_fts")
    op.drop_index("ix_chunks_tenant_id", table_name="chunks")
    op.drop_table("chunks")
    op.drop_table("document_links")
    op.drop_index("ix_documents_tenant_id", table_name="documents")
    op.drop_table("documents")
    op.drop_table("source_versions")
    op.drop_index("ix_sources_tenant_id", table_name="sources")
    op.drop_table("sources")
    op.drop_table("user_group_memberships")
    op.drop_table("users")
    op.drop_table("tenant_group_bindings")
    op.drop_table("local_groups")
    op.drop_table("tenant_settings")
    op.drop_table("tenants")

    for enum_name in [
        "only_sources_verdict",
        "log_data_mode",
        "event_type",
        "pipeline_stage_status",
        "pipeline_stage",
        "link_type",
        "job_status",
        "job_type",
        "only_sources_mode",
        "citations_mode",
        "tenant_role",
        "source_status",
        "source_type",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
