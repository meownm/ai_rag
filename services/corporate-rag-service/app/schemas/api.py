from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "corporate-rag-service"
    version: str


class QueryRequest(BaseModel):
    tenant_id: UUID
    query: str
    citations: bool | None = None
    top_k: int = Field(default=10, ge=1, le=50)
    filters: dict[str, Any] | None = None


class ScoreBreakdown(BaseModel):
    lex_score: float
    vec_score: float
    rerank_score: float
    boosts: dict[str, float]
    final_score: float


class Citation(BaseModel):
    chunk_id: UUID
    document_id: UUID
    title: str
    url: str
    snippet: str
    score_breakdown: ScoreBreakdown | None = None




class TraceScoreEntry(BaseModel):
    chunk_id: UUID
    lex_score: float
    vec_score: float
    rerank_score: float
    boosts_applied: list[dict[str, Any]]
    final_score: float
    rank_position: int


class QueryTrace(BaseModel):
    trace_id: UUID
    scoring_trace: list[TraceScoreEntry]


class QueryResponse(BaseModel):
    answer: str
    only_sources_verdict: str
    citations: list[Citation] = []
    correlation_id: UUID
    trace: QueryTrace | None = None


class SourceSyncRequest(BaseModel):
    tenant_id: UUID
    source_types: list[str]
    force_reindex: bool = False


class JobAcceptedResponse(BaseModel):
    job_id: UUID
    job_status: str


class ErrorInfo(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    correlation_id: UUID
    retryable: bool
    timestamp: datetime


class ErrorEnvelope(BaseModel):
    error: ErrorInfo


class JobStatusResponse(BaseModel):
    job_id: UUID
    tenant_id: UUID
    job_type: str
    job_status: str
    requested_by: str
    started_at: datetime
    finished_at: datetime | None = None
    error: ErrorEnvelope | None = None
