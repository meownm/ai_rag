import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.models import Chunks, ChunkVectors, Documents, IngestJobs
from app.schemas.api import (
    ErrorEnvelope,
    ErrorInfo,
    HealthResponse,
    JobAcceptedResponse,
    JobStatusResponse,
    QueryRequest,
    QueryResponse,
    SourceSyncRequest,
)
from app.services.anti_hallucination import verify_answer
from app.services.audit import log_event
from app.services.embeddings_client import EmbeddingsClient
from app.services.reranker import RerankerService
from app.services.retrieval import hybrid_rank

router = APIRouter()


@lru_cache
def get_reranker() -> RerankerService:
    return RerankerService(settings.reranker_model_id)


@lru_cache
def get_embeddings_client() -> EmbeddingsClient:
    return EmbeddingsClient(settings.embeddings_service_url)


def _error(code: str, message: str, correlation_id: uuid.UUID, retryable: bool, status_code: int) -> HTTPException:
    envelope = ErrorEnvelope(
        error=ErrorInfo(
            code=code,
            message=message,
            details=None,
            correlation_id=correlation_id,
            retryable=retryable,
            timestamp=datetime.now(timezone.utc),
        )
    )
    return HTTPException(status_code=status_code, detail=envelope.model_dump())


@router.get("/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(version=settings.app_version)


@router.post("/v1/ingest/sources/sync", response_model=JobAcceptedResponse, status_code=202)
def start_source_sync(payload: SourceSyncRequest, db: Session = Depends(get_db)) -> JobAcceptedResponse:
    job = IngestJobs(tenant_id=payload.tenant_id, job_type="REINDEX_ALL", job_status="queued", requested_by="api")
    db.add(job)
    db.commit()
    db.refresh(job)
    return JobAcceptedResponse(job_id=job.job_id, job_status=job.job_status)


@router.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> JobStatusResponse:
    job = db.query(IngestJobs).filter(IngestJobs.job_id == job_id).first()
    if not job:
        raise _error("SOURCE_NOT_FOUND", "Job not found", uuid.uuid4(), False, status.HTTP_404_NOT_FOUND)
    return JobStatusResponse(
        job_id=job.job_id,
        tenant_id=job.tenant_id,
        job_type=job.job_type,
        job_status=job.job_status,
        requested_by=job.requested_by,
        started_at=job.started_at,
    )


def _fetch_candidates(db: Session, tenant_id: str, top_n: int) -> list[dict]:
    rows = (
        db.query(Chunks, Documents, ChunkVectors)
        .join(Documents, Documents.document_id == Chunks.document_id)
        .join(ChunkVectors, ChunkVectors.chunk_id == Chunks.chunk_id)
        .filter(Chunks.tenant_id == tenant_id)
        .order_by(Chunks.ordinal.asc())
        .limit(top_n)
        .all()
    )

    return [
        {
            "chunk_id": chunk.chunk_id,
            "document_id": document.document_id,
            "chunk_text": chunk.chunk_text,
            "title": document.title,
            "url": document.url or "",
            "heading_path": chunk.chunk_path.split("/") if chunk.chunk_path else [],
            "labels": document.labels or [],
            "author": document.author,
            "updated_at": document.updated_date.isoformat() if document.updated_date else "",
            "embedding": list(vector.embedding),
        }
        for chunk, document, vector in rows
    ]


@router.post("/v1/query", response_model=QueryResponse)
def post_query(payload: QueryRequest, db: Session = Depends(get_db)) -> QueryResponse:
    corr = uuid.uuid4()
    t0 = time.perf_counter()
    log_event(db, str(payload.tenant_id), str(corr), "API_REQUEST", payload.model_dump())

    try:
        query_embedding = get_embeddings_client().embed(
            model="bge-m3",
            texts=[payload.query],
            tenant_id=str(payload.tenant_id),
            correlation_id=str(corr),
        )[0]
    except Exception as exc:  # noqa: BLE001
        log_event(db, str(payload.tenant_id), str(corr), "ERROR", {"code": "EMBEDDINGS_HTTP_ERROR", "message": str(exc)})
        raise _error("EMBEDDINGS_HTTP_ERROR", "Embeddings service call failed", corr, True, status.HTTP_500_INTERNAL_SERVER_ERROR)

    candidates = _fetch_candidates(db, str(payload.tenant_id), max(payload.top_k, settings.rerank_top_n))

    ranked, timers = hybrid_rank(payload.query, candidates, query_embedding)
    reranked, t_rerank = get_reranker().rerank(payload.query, ranked)
    ranked_final, _ = hybrid_rank(payload.query, reranked, query_embedding)

    chosen = ranked_final[: payload.top_k]
    answer = " ".join([c["chunk_text"] for c in chosen[:2]]) if chosen else ""
    valid, anti_payload = verify_answer(
        answer,
        [c["chunk_text"] for c in chosen],
        settings.min_sentence_similarity,
        settings.min_lexical_overlap,
    )

    only_sources = "PASS"
    if not chosen or not valid:
        answer = "Insufficient evidence in retrieved sources."
        only_sources = "FAIL"

    total_ms = int((time.perf_counter() - t0) * 1000)
    perf = {"t_parse_ms": 1, **timers, "t_rerank_ms": t_rerank, "t_total_ms": total_ms, "t_llm_ms": 0, "t_citations_ms": 1}
    if total_ms > 1200:
        log_event(db, str(payload.tenant_id), str(corr), "ERROR", {"message": "perf_budget_exceeded", **perf})

    citations = [
        {
            "chunk_id": c["chunk_id"],
            "document_id": c["document_id"],
            "title": c["title"],
            "url": c["url"],
            "snippet": c["chunk_text"][:200],
            "score_breakdown": {
                "lex_score": c["lex_score"],
                "vec_score": c["vec_score"],
                "rerank_score": c["rerank_score"],
                "boosts": {b["name"]: b["value"] for b in c["boosts_applied"]},
                "final_score": c["final_score"],
            },
        }
        for c in chosen
    ]

    trace = {
        "trace_id": str(corr),
        "scoring_trace": [
            {
                "chunk_id": str(c["chunk_id"]),
                "lex_score": c["lex_score"],
                "vec_score": c["vec_score"],
                "rerank_score": c["rerank_score"],
                "boosts_applied": c["boosts_applied"],
                "final_score": c["final_score"],
                "rank_position": c["rank_position"],
                "headings_path": c["heading_path"],
                "title": c["title"],
                "labels": c["labels"],
                "author": c["author"],
                "updated_at": c["updated_at"],
                "source_url": c["url"],
            }
            for c in chosen
        ],
        "anti_hallucination": anti_payload,
        "timing": perf,
    }
    log_event(db, str(payload.tenant_id), str(corr), "API_RESPONSE", trace, duration_ms=total_ms)
    return QueryResponse(answer=answer, only_sources_verdict=only_sources, citations=citations if payload.citations else [], correlation_id=corr)
