import json
import re
import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.clients.embeddings_client import EmbeddingsClient
from app.clients.ollama_client import OllamaClient
from app.core.config import settings
from app.db.repositories import TenantRepository
from app.db.session import get_db
from app.models.models import IngestJobs
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
from app.services.ingestion import ingest_sources_sync
from app.services.performance import build_stage_budgets, exceeded_budgets
from app.services.query_pipeline import apply_context_budget, expand_neighbors
from app.services.reranker import RerankerService
from app.services.retrieval import hybrid_rank
from app.services.scoring_trace import build_scoring_trace

router = APIRouter()

@lru_cache
def get_reranker() -> RerankerService:
    return RerankerService(settings.RERANKER_MODEL)


@lru_cache
def get_embeddings_client() -> EmbeddingsClient:
    return EmbeddingsClient(settings.EMBEDDINGS_SERVICE_URL, settings.EMBEDDINGS_TIMEOUT_SECONDS)


@lru_cache
def get_ollama_client() -> OllamaClient:
    return OllamaClient(settings.LLM_ENDPOINT, settings.LLM_MODEL, settings.REQUEST_TIMEOUT_SECONDS)


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


def _extract_json_payload(raw: str) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}


def _build_llm_prompt(query: str, contexts: list[dict]) -> str:
    context_blocks = []
    for c in contexts:
        heading = "/".join(c.get("heading_path", []))
        context_blocks.append(
            f"[CHUNK chunk_id={c['chunk_id']} doc_title={c.get('title','')} headings={heading} url={c.get('url','')}]\n{c['chunk_text']}"
        )
    blocks = "\n\n".join(context_blocks)
    return (
        "You are a grounded enterprise RAG assistant. Use only provided chunks. "
        "Every key claim must include citation chunk_ids from provided chunks. "
        "Return STRICT JSON only:\n"
        '{"status":"success","answer":"...","citations":[{"chunk_id":"...","quote":"..."}]}'
        "\nIf evidence is insufficient return:\n"
        '{"status":"insufficient_evidence","message":"..."}'
        f"\nQuestion: {query}\n\nContext:\n{blocks}"
    )


def _fetch_candidates(db: Session, tenant_id: str, query: str, query_embedding: list[float], top_n: int) -> tuple[list[dict], int]:
    repo = TenantRepository(db, tenant_id)
    k_lex = max(top_n, settings.DEFAULT_TOP_K)
    k_vec = max(top_n, settings.RERANKER_TOP_K)

    t0 = time.perf_counter()
    lexical_scores = repo.fetch_lexical_candidate_scores(query, k_lex)
    lexical_ms = int((time.perf_counter() - t0) * 1000)
    vector_candidates = repo.fetch_vector_candidates(query_embedding, k_vec)
    vector_score_map = {c["chunk_id"]: c["vec_score"] for c in vector_candidates}

    chunk_ids = set(lexical_scores.keys()) | set(vector_score_map.keys())
    candidates = repo.hydrate_candidates(chunk_ids, lexical_scores, vector_score_map)
    return candidates, lexical_ms


@router.get("/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(version=settings.APP_VERSION)


@router.post("/v1/ingest/sources/sync", response_model=JobAcceptedResponse, status_code=202)
def start_source_sync(payload: SourceSyncRequest, db: Session = Depends(get_db)) -> JobAcceptedResponse:
    repo = TenantRepository(db, payload.tenant_id)
    job = repo.create_job(job_type="REINDEX_ALL", requested_by="api")

    try:
        ingest_sources_sync(db, payload.tenant_id, payload.source_types)
        repo.mark_job(job, "done")
    except Exception as exc:  # noqa: BLE001
        repo.mark_job(job, "error", error_code="SOURCE_FETCH_FAILED", error_message=str(exc))
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


@router.post("/v1/query", response_model=QueryResponse)
def post_query(payload: QueryRequest, db: Session = Depends(get_db)) -> QueryResponse:
    corr = uuid.uuid4()
    t_start = time.perf_counter()
    log_event(db, str(payload.tenant_id), str(corr), "API_REQUEST", payload.model_dump())

    try:
        log_event(db, str(payload.tenant_id), str(corr), "EMBEDDINGS_REQUEST", {"query": payload.query, "model": "bge-m3"})
        query_embedding = get_embeddings_client().embed_text(payload.query, tenant_id=str(payload.tenant_id), correlation_id=str(corr))
        log_event(db, str(payload.tenant_id), str(corr), "EMBEDDINGS_RESPONSE", {"dimensions": len(query_embedding)})
    except Exception as exc:  # noqa: BLE001
        log_event(db, str(payload.tenant_id), str(corr), "ERROR", {"code": "EMBEDDINGS_HTTP_ERROR", "message": str(exc)})
        raise _error("EMBEDDINGS_HTTP_ERROR", "Embeddings service call failed", corr, True, status.HTTP_500_INTERNAL_SERVER_ERROR)

    t_parse0 = time.perf_counter()
    candidates, lexical_ms = _fetch_candidates(db, str(payload.tenant_id), payload.query, query_embedding, max(payload.top_k, settings.RERANKER_TOP_K))
    t_parse_ms = int((time.perf_counter() - t_parse0) * 1000)

    ranked, timers = hybrid_rank(payload.query, candidates, query_embedding)
    reranked, t_rerank = get_reranker().rerank(payload.query, ranked)
    ranked_final, _ = hybrid_rank(payload.query, reranked, query_embedding)
    tenant_safe_ranked = [c for c in ranked_final if c.get("tenant_id") == str(payload.tenant_id)]
    chosen = expand_neighbors(db, str(payload.tenant_id), tenant_safe_ranked, payload.top_k)
    chosen, budget_log = apply_context_budget(chosen)

    only_sources = "PASS"
    if not chosen:
        answer = build_structured_refusal(str(corr), {"reason": "no_sources"})
        anti_payload = {"refusal_triggered": True, "unsupported_sentences": 0}
        only_sources = "FAIL"
    else:
        prompt = _build_llm_prompt(payload.query, chosen)
        llm_start = time.perf_counter()
        try:
            log_event(db, str(payload.tenant_id), str(corr), "LLM_REQUEST", {"model": settings.LLM_MODEL, "prompt": prompt})
            llm_payload = get_ollama_client().generate(prompt)
            log_event(db, str(payload.tenant_id), str(corr), "LLM_RESPONSE", {"raw": llm_payload})
            if isinstance(llm_payload, dict):
                llm_raw = str(llm_payload.get("response", ""))
            else:
                llm_raw = str(llm_payload)
        except Exception as exc:  # noqa: BLE001
            llm_raw = ""
            log_event(db, str(payload.tenant_id), str(corr), "ERROR", {"code": "LLM_PROVIDER_ERROR", "message": str(exc)})
        t_llm_ms = int((time.perf_counter() - llm_start) * 1000)

        parsed = _extract_json_payload(llm_raw)
        citations_from_model = parsed.get("citations") if isinstance(parsed, dict) else None
        if parsed.get("status") != "success" or not citations_from_model:
            answer = build_structured_refusal(str(corr), {"reason": "insufficient_evidence", "raw": llm_raw})
            anti_payload = {"refusal_triggered": True, "unsupported_sentences": 0}
            only_sources = "FAIL"
        else:
            answer = str(parsed.get("answer", "")).strip()
            valid, anti_payload = verify_answer(
                answer,
                [c["chunk_text"] for c in chosen],
                settings.MIN_SENTENCE_SIMILARITY,
                settings.MIN_LEXICAL_OVERLAP,
            )
            if not valid or not answer:
                answer = build_structured_refusal(str(corr), anti_payload)
                only_sources = "FAIL"
    t_llm_ms = locals().get("t_llm_ms", 0)

    t_citations0 = time.perf_counter()
    citations = [
        {
            "chunk_id": c["chunk_id"],
            "document_id": c["document_id"],
            "title": c["title"],
            "url": c["url"],
            "snippet": c["chunk_text"][:200],
            "score_breakdown": {
                "lex_score": c.get("lex_score", 0.0),
                "vec_score": c.get("vec_score", 0.0),
                "rerank_score": c.get("rerank_score", 0.0),
                "boosts": {b["name"]: b["value"] for b in c.get("boosts_applied", [])},
                "final_score": c.get("final_score", 0.0),
            },
        }
        for c in chosen
    ]

    t_citations_ms = int((time.perf_counter() - t_citations0) * 1000)
    t_total_ms = int((time.perf_counter() - t_start) * 1000)
    perf = {
        "t_parse_ms": t_parse_ms,
        **timers,
        "t_lexical_ms": lexical_ms,
        "t_rerank_ms": t_rerank,
        "t_total_ms": t_total_ms,
        "t_llm_ms": t_llm_ms,
        "t_citations_ms": t_citations_ms,
        **budget_log,
    }
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
