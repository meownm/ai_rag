import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
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
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    source_type: Mapped[str] = mapped_column(Enum(*SOURCE_TYPE, name="source_type"))
    external_ref: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(Enum(*SOURCE_STATUS, name="source_status"), default="DISCOVERED")


class SourceVersions(Base):
    __tablename__ = "source_versions"
    source_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
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
    chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    fts_doc: Mapped[str] = mapped_column(Text)


class SearchRequests(Base):
    __tablename__ = "search_requests"
    search_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    query_text: Mapped[str] = mapped_column(Text)
    citations_requested: Mapped[bool] = mapped_column()
