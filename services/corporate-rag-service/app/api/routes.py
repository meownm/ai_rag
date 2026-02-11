import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
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
from app.services.anti_hallucination import build_structured_refusal, verify_answer
from app.services.audit import log_event
from app.services.embeddings_client import EmbeddingsClient
from app.services.ingestion import ingest_sources_sync
from app.services.performance import build_stage_budgets, exceeded_budgets
from app.services.reranker import RerankerService
from app.services.retrieval import hybrid_rank
from app.services.scoring_trace import build_scoring_trace

router = APIRouter()


@lru_cache
def get_reranker() -> RerankerService:
    return RerankerService(settings.RERANKER_MODEL)


@lru_cache
def get_embeddings_client() -> EmbeddingsClient:
    return EmbeddingsClient(settings.EMBEDDINGS_SERVICE_URL)


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
    return HealthResponse(version=settings.APP_VERSION)


@router.post("/v1/ingest/sources/sync", response_model=JobAcceptedResponse, status_code=202)
def start_source_sync(payload: SourceSyncRequest, db: Session = Depends(get_db)) -> JobAcceptedResponse:
    job = IngestJobs(tenant_id=payload.tenant_id, job_type="REINDEX_ALL", job_status="processing", requested_by="api")
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        ingest_sources_sync(db, payload.tenant_id, payload.source_types)
        job.job_status = "done"
        job.finished_at = datetime.now(timezone.utc)
        db.add(job)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        job.job_status = "error"
        job.error_code = "SOURCE_FETCH_FAILED"
        job.error_message = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        db.add(job)
        db.commit()
        raise

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


def _fetch_lexical_candidate_scores(db: Session, tenant_id: str, query: str, top_n: int) -> tuple[dict[str, float], int]:
    t0 = time.perf_counter()
    rows = db.execute(
        text(
            """
            SELECT cf.chunk_id::text AS chunk_id,
                   ts_rank_cd(cf.fts_doc, plainto_tsquery('simple', :query_text)) AS lex_score
            FROM chunk_fts cf
            WHERE cf.tenant_id = CAST(:tenant_id AS uuid)
              AND cf.fts_doc @@ plainto_tsquery('simple', :query_text)
            ORDER BY lex_score DESC
            LIMIT :limit_n
            """
        ),
        {"tenant_id": tenant_id, "query_text": query, "limit_n": top_n},
    ).mappings().all()
    lexical_ms = int((time.perf_counter() - t0) * 1000)
    return {row["chunk_id"]: float(row["lex_score"] or 0.0) for row in rows}, lexical_ms


def _fetch_vector_candidates(db: Session, tenant_id: str, top_n: int) -> list[dict]:
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
            "chunk_id": str(chunk.chunk_id),
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


def _fetch_candidates(db: Session, tenant_id: str, query: str, top_n: int) -> tuple[list[dict], int]:
    k_lex = max(top_n, settings.DEFAULT_TOP_K)
    k_vec = max(top_n, settings.RERANKER_TOP_K)

    lexical_scores, lexical_ms = _fetch_lexical_candidate_scores(db, tenant_id, query, k_lex)
    vector_candidates = _fetch_vector_candidates(db, tenant_id, k_vec)

    chunk_ids = set(lexical_scores.keys()) | {c["chunk_id"] for c in vector_candidates}

    rows = (
        db.query(Chunks, Documents, ChunkVectors)
        .join(Documents, Documents.document_id == Chunks.document_id)
        .join(ChunkVectors, ChunkVectors.chunk_id == Chunks.chunk_id)
        .filter(Chunks.tenant_id == tenant_id)
        .filter(Chunks.chunk_id.in_(chunk_ids))
        .all()
    ) if chunk_ids else []

    candidates = [
        {
            "chunk_id": str(chunk.chunk_id),
            "document_id": document.document_id,
            "chunk_text": chunk.chunk_text,
            "title": document.title,
            "url": document.url or "",
            "heading_path": chunk.chunk_path.split("/") if chunk.chunk_path else [],
            "labels": document.labels or [],
            "author": document.author,
            "updated_at": document.updated_date.isoformat() if document.updated_date else "",
            "embedding": list(vector.embedding),
            "lex_score": lexical_scores.get(str(chunk.chunk_id), 0.0),
        }
        for chunk, document, vector in rows
    ]
    return candidates, lexical_ms


@router.post("/v1/query", response_model=QueryResponse)
def post_query(payload: QueryRequest, db: Session = Depends(get_db)) -> QueryResponse:
    corr = uuid.uuid4()
    t_start = time.perf_counter()
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

    t_parse0 = time.perf_counter()
    candidates, lexical_ms = _fetch_candidates(db, str(payload.tenant_id), payload.query, max(payload.top_k, settings.RERANKER_TOP_K))
    t_parse_ms = int((time.perf_counter() - t_parse0) * 1000)

    ranked, timers = hybrid_rank(payload.query, candidates, query_embedding)
    reranked, t_rerank = get_reranker().rerank(payload.query, ranked)
    ranked_final, _ = hybrid_rank(payload.query, reranked, query_embedding)

    chosen = ranked_final[: payload.top_k]
    answer = " ".join([c["chunk_text"] for c in chosen[:2]]) if chosen else ""
    valid, anti_payload = verify_answer(
        answer,
        [c["chunk_text"] for c in chosen],
        settings.MIN_SENTENCE_SIMILARITY,
        settings.MIN_LEXICAL_OVERLAP,
    )

    only_sources = "PASS"
    if not chosen or not valid:
        answer = build_structured_refusal(str(corr), anti_payload)
        only_sources = "FAIL"

    t_citations0 = time.perf_counter()
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

    t_citations_ms = int((time.perf_counter() - t_citations0) * 1000)
    t_total_ms = int((time.perf_counter() - t_start) * 1000)
    perf = {"t_parse_ms": t_parse_ms, **timers, "t_lexical_ms": lexical_ms, "t_rerank_ms": t_rerank, "t_total_ms": t_total_ms, "t_llm_ms": 0, "t_citations_ms": t_citations_ms}
    budgets = build_stage_budgets(settings.REQUEST_TIMEOUT_SECONDS, settings.EMBEDDINGS_TIMEOUT_SECONDS)
    exceeded = exceeded_budgets(perf, budgets)
    if exceeded:
        log_event(db, str(payload.tenant_id), str(corr), "ERROR", {"message": "perf_budget_exceeded", "exceeded": exceeded, "perf": perf, "budgets": budgets})

    trace = build_scoring_trace(str(corr), chosen)
    trace["anti_hallucination"] = anti_payload
    trace["timing"] = perf

    log_event(db, str(payload.tenant_id), str(corr), "PIPELINE_STAGE", {"stage": "FUSION_BOOST", "trace_id": trace["trace_id"], "scoring_trace": trace["scoring_trace"], "timing": perf})
    log_event(db, str(payload.tenant_id), str(corr), "API_RESPONSE", trace, duration_ms=t_total_ms)
    return QueryResponse(
        answer=answer,
        only_sources_verdict=only_sources,
        citations=citations if payload.citations else [],
        correlation_id=corr,
        trace={"trace_id": corr, "scoring_trace": trace["scoring_trace"]},
    )
