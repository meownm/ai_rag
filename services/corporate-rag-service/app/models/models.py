import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Index, Integer, PrimaryKeyConstraint, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


SOURCE_TYPE = ("CONFLUENCE_PAGE", "CONFLUENCE_ATTACHMENT", "FILE_CATALOG_OBJECT")
SOURCE_STATUS = ("DISCOVERED", "FETCHED", "NORMALIZED", "INDEXED", "FAILED")
TENANT_ROLE = ("TENANT_ADMIN", "TENANT_EDITOR", "TENANT_VIEWER")
CITATIONS_MODE = ("DISABLED", "OPTIONAL", "REQUIRED")
ONLY_SOURCES_MODE = ("STRICT",)
JOB_TYPE = ("SYNC_CONFLUENCE", "SYNC_FILE_CATALOG", "PREPROCESS", "INDEX_LEXICAL", "INDEX_VECTOR", "REINDEX_ALL")
JOB_STATUS = ("queued", "processing", "retrying", "done", "error", "canceled", "expired")
LINK_TYPE = ("CONFLUENCE_PAGE_LINK", "EXTERNAL_URL", "ATTACHMENT_LINK")
PIPELINE_STAGE = (
    "INGEST_DISCOVERY", "INGEST_FETCH", "NORMALIZE_MARKDOWN", "STRUCTURE_PARSE", "CHUNK_LOGICAL",
    "INDEX_BM25", "EMBED_REQUEST", "INDEX_VECTOR", "SEARCH_LEXICAL", "SEARCH_VECTOR", "FUSION_BOOST",
    "RERANK", "ANSWER_COMPOSE", "ANSWER_VALIDATE_ONLY_SOURCES",
)
PIPELINE_STAGE_STATUS = ("STARTED", "COMPLETED", "FAILED", "SKIPPED")
EVENT_TYPE = ("API_REQUEST", "API_RESPONSE", "EMBEDDINGS_REQUEST", "EMBEDDINGS_RESPONSE", "LLM_REQUEST", "LLM_RESPONSE", "PIPELINE_STAGE", "ERROR")
LOG_DATA_MODE = ("PLAIN", "MASKED", "HASHED")
ERROR_CODE = (
    "AUTH_UNAUTHORIZED", "AUTH_FORBIDDEN_TENANT", "TENANT_NOT_FOUND", "SOURCE_NOT_FOUND", "SOURCE_FETCH_FAILED",
    "NORMALIZATION_FAILED", "CHUNKING_FAILED", "EMBEDDINGS_HTTP_ERROR", "EMBEDDINGS_TIMEOUT", "VECTOR_INDEX_ERROR",
    "LEXICAL_INDEX_ERROR", "RERANKER_ERROR", "ONLY_SOURCES_VIOLATION", "LLM_PROVIDER_ERROR", "VALIDATION_ERROR",
    "RATE_LIMITED", "INTERNAL_ERROR",
)
ONLY_SOURCES_VERDICT = ("PASS", "FAIL")
CONVERSATION_STATUS = ("active", "archived")
CONVERSATION_ROLE = ("user", "assistant", "system")
REWRITE_STRATEGY = ("none", "llm_rewrite")


class Tenants(Base):
    __tablename__ = "tenants"
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_key: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(255))


class TenantSettings(Base):
    __tablename__ = "tenant_settings"
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), primary_key=True)
    citations_mode: Mapped[str] = mapped_column(Enum(*CITATIONS_MODE, name="citations_mode"))
    only_sources_mode: Mapped[str] = mapped_column(Enum(*ONLY_SOURCES_MODE, name="only_sources_mode"), default="STRICT")


class Documents(Base):
    __tablename__ = "documents"
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    title: Mapped[str] = mapped_column(String(512))
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    labels: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Chunks(Base):
    __tablename__ = "chunks"
    chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.document_id"), index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    chunk_path: Mapped[str] = mapped_column(String(1024))
    chunk_text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)
    ordinal: Mapped[int] = mapped_column(Integer)
    chunk_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    char_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    block_start_idx: Mapped[int | None] = mapped_column(Integer, nullable=True)
    block_end_idx: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ChunkVectors(Base):
    __tablename__ = "chunk_vectors"
    chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chunks.chunk_id"), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    embedding_model: Mapped[str] = mapped_column(String(255))
    embedding = mapped_column(Vector(1024))
    embedding_dim: Mapped[int] = mapped_column(Integer)


class IngestJobs(Base):
    __tablename__ = "ingest_jobs"
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    job_type: Mapped[str] = mapped_column(Enum(*JOB_TYPE, name="job_type"))
    job_status: Mapped[str] = mapped_column(Enum(*JOB_STATUS, name="job_status"), default="queued")
    requested_by: Mapped[str] = mapped_column(String(255))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class SearchCandidates(Base):
    __tablename__ = "search_candidates"
    search_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    lex_score: Mapped[float] = mapped_column(Float)
    vec_score: Mapped[float] = mapped_column(Float)
    rerank_score: Mapped[float] = mapped_column(Float)
    boosts_json: Mapped[dict] = mapped_column(JSON)
    final_score: Mapped[float] = mapped_column(Float)
    rank_position: Mapped[int] = mapped_column(Integer)


class Answers(Base):
    __tablename__ = "answers"
    answer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    answer_text: Mapped[str] = mapped_column(Text)
    only_sources_verdict: Mapped[str] = mapped_column(Enum(*ONLY_SOURCES_VERDICT, name="only_sources_verdict"))
    citations_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class PipelineTrace(Base):
    __tablename__ = "pipeline_trace"
    trace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    stage: Mapped[str] = mapped_column(Enum(*PIPELINE_STAGE, name="pipeline_stage"))
    status: Mapped[str] = mapped_column(Enum(*PIPELINE_STAGE_STATUS, name="pipeline_stage_status"))
    payload_json: Mapped[dict] = mapped_column(JSON)


class EventLogs(Base):
    __tablename__ = "event_logs"
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    event_type: Mapped[str] = mapped_column(Enum(*EVENT_TYPE, name="event_type"))
    log_data_mode: Mapped[str] = mapped_column(Enum(*LOG_DATA_MODE, name="log_data_mode"), default="PLAIN")
    payload_json: Mapped[dict] = mapped_column(JSON)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

class LocalGroups(Base):
    __tablename__ = "local_groups"
    group_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_name: Mapped[str] = mapped_column(String(255), unique=True)


class TenantGroupBindings(Base):
    __tablename__ = "tenant_group_bindings"
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    group_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[str] = mapped_column(Enum(*TENANT_ROLE, name="tenant_role"))


class Users(Base):
    __tablename__ = "users"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    principal_name: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255))


class UserGroupMemberships(Base):
    __tablename__ = "user_group_memberships"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    group_id: Mapped[int] = mapped_column(Integer, primary_key=True)


class Sources(Base):
    __tablename__ = "sources"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source_type", "external_ref", name="uq_sources_tenant_type_external_ref"),
    )
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    source_type: Mapped[str] = mapped_column(Enum(*SOURCE_TYPE, name="source_type"))
    external_ref: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(Enum(*SOURCE_STATUS, name="source_status"), default="DISCOVERED")


class SourceVersions(Base):
    __tablename__ = "source_versions"
    __table_args__ = (
        UniqueConstraint("source_id", "checksum", name="uq_source_versions_source_checksum"),
        Index("ix_source_versions_source_id", "source_id"),
    )
    source_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    version_label: Mapped[str] = mapped_column(String(255))
    checksum: Mapped[str] = mapped_column(String(255))
    s3_raw_uri: Mapped[str] = mapped_column(String(1024))
    s3_markdown_uri: Mapped[str] = mapped_column(String(1024))
    metadata_json: Mapped[dict] = mapped_column(JSON)


class DocumentLinks(Base):
    __tablename__ = "document_links"
    from_document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    to_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    link_url: Mapped[str] = mapped_column(String(2048), primary_key=True)
    link_type: Mapped[str] = mapped_column(Enum(*LINK_TYPE, name="link_type"))


class ChunkFTS(Base):
    __tablename__ = "chunk_fts"
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True)
    chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chunks.chunk_id"), primary_key=True)
    fts_doc: Mapped[str] = mapped_column(TSVECTOR, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SearchRequests(Base):
    __tablename__ = "search_requests"
    search_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    query_text: Mapped[str] = mapped_column(Text)
    citations_requested: Mapped[bool] = mapped_column()


class Conversations(Base):
    __tablename__ = "conversations"
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    status: Mapped[str] = mapped_column(Enum(*CONVERSATION_STATUS, name="conversation_status"), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ConversationTurns(Base):
    __tablename__ = "conversation_turns"
    __table_args__ = (UniqueConstraint("conversation_id", "turn_index", name="uq_conversation_turns_conversation_turn_index"),)
    turn_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.conversation_id"), index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    turn_index: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(Enum(*CONVERSATION_ROLE, name="conversation_role"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class QueryResolutions(Base):
    __tablename__ = "query_resolutions"
    resolution_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    turn_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversation_turns.turn_id"), index=True)
    resolved_query_text: Mapped[str] = mapped_column(Text)
    rewrite_strategy: Mapped[str] = mapped_column(Enum(*REWRITE_STRATEGY, name="rewrite_strategy"), default="none")
    rewrite_inputs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rewrite_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    topic_shift_detected: Mapped[bool] = mapped_column(default=False)
    needs_clarification: Mapped[bool] = mapped_column(default=False)
    clarification_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RetrievalTraceItems(Base):
    __tablename__ = "retrieval_trace_items"
    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "conversation_id", "turn_id", "document_id", "chunk_id", "ordinal", name="pk_retrieval_trace_items"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    turn_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    ordinal: Mapped[int] = mapped_column(Integer)
    score_lex_raw: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_vec_raw: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_rerank_raw: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_final: Mapped[float | None] = mapped_column(Float, nullable=True)
    used_in_context: Mapped[bool] = mapped_column(default=False)
    used_in_answer: Mapped[bool] = mapped_column(default=False)
    citation_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ConversationSummaries(Base):
    __tablename__ = "conversation_summaries"
    __table_args__ = (
        UniqueConstraint("tenant_id", "conversation_id", "summary_version", name="uq_conversation_summaries_tenant_conversation_version"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    summary_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    summary_text: Mapped[str] = mapped_column(Text)
    covers_turn_index_to: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
