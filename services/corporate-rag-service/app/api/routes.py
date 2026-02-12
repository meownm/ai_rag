import json
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import logging

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.clients.embeddings_client import EmbeddingsClient
from app.clients.ollama_client import OllamaClient
from app.core.config import settings
from app.db.repositories import ConversationRepository, TenantRepository
from app.db.session import get_db
from app.models.models import IngestJobs
from app.schemas.api import (
    ErrorEnvelope,
    ErrorInfo,
    HealthResponse,
    MetricSummary,
    MetricsResponse,
    ReadinessCheck,
    ReadinessResponse,
    JobAcceptedResponse,
    JobListResponse,
    JobStatusResponse,
    QueryRequest,
    QueryResponse,
    SourceSyncRequest,
)
from app.services.anti_hallucination import build_structured_refusal, verify_answer
from app.services.agent_pipeline import (
    AgentPipeline,
    AgentPipelineRequest,
    AnalysisAgentInput,
    AnswerAgentInput,
    RetrievalAgentInput,
    RewriteAgentInput,
)
from app.services.audit import log_event
from app.services.file_ingestion import FileByteIngestor
from app.services.ingestion import ingest_source_items
from app.services.performance import build_stage_budgets, exceeded_budgets
from app.services.query_pipeline import apply_context_budget, expand_neighbors
from app.services.reranker import RerankerService
from app.services.retrieval import hybrid_rank
from app.services.scoring_trace import build_scoring_trace
from app.services.security import InMemoryRateLimiter, sanitize_user_query
from app.services.telemetry import emit_metric, log_stage_latency, metric_samples
from app.runners.conversation_summarizer import ConversationSummarizer
from app.runners.query_rewriter import QueryRewriteError, QueryRewriter

router = APIRouter()
logger = logging.getLogger(__name__)


rate_limiter = InMemoryRateLimiter(
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    per_user_limit=settings.RATE_LIMIT_PER_USER,
    burst_limit=settings.RATE_LIMIT_BURST,
    max_users=settings.RATE_LIMIT_STORAGE_MAX_USERS,
)

@lru_cache
def get_reranker() -> RerankerService:
    return RerankerService(settings.RERANKER_MODEL)


@lru_cache
def get_embeddings_client() -> EmbeddingsClient:
    return EmbeddingsClient(settings.EMBEDDINGS_SERVICE_URL, settings.EMBEDDINGS_TIMEOUT_SECONDS)


@lru_cache
def get_ollama_client() -> OllamaClient:
    return OllamaClient(settings.LLM_ENDPOINT, settings.LLM_MODEL, settings.REQUEST_TIMEOUT_SECONDS)


def get_agent_pipeline() -> AgentPipeline:
    return AgentPipeline()


def get_query_rewriter() -> QueryRewriter:
    return QueryRewriter(model_id=settings.REWRITE_MODEL_ID, keep_alive=settings.REWRITE_KEEP_ALIVE)


def get_conversation_summarizer() -> ConversationSummarizer:
    return ConversationSummarizer(model_id=settings.REWRITE_MODEL_ID)


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


def _estimate_token_count(text: str) -> int:
    words = len(text.split())
    return max(1, int(words * 1.33)) if text.strip() else 0


def _build_retrieval_only_answer(contexts: list[dict]) -> str:
    selected = [c.get("chunk_text", "").strip() for c in contexts[:2] if c.get("chunk_text", "").strip()]
    return "\n\n".join(selected)


def _is_plain_log_mode() -> bool:
    return settings.LOG_DATA_MODE.strip().lower() == "plain"


def _is_debug_allowed(debug_requested: bool, user_role: str | None) -> bool:
    if not debug_requested:
        return False
    return (user_role or "").strip().lower() == settings.DEBUG_ADMIN_ROLE.strip().lower()


def _fetch_candidates(db: Session, tenant_id: str, query: str, query_embedding: list[float], top_n: int) -> tuple[list[dict], int]:
    repo = TenantRepository(db, tenant_id)
    k_lex = max(top_n, settings.DEFAULT_TOP_K)
    k_vec = max(top_n, settings.RERANKER_TOP_K)

    t0 = time.perf_counter()
    lexical_scores = repo.fetch_lexical_candidate_scores(query, k_lex)
    lexical_ms = int((time.perf_counter() - t0) * 1000)
    vector_candidates = repo.fetch_vector_candidates(query_embedding, k_vec, use_similarity=settings.USE_VECTOR_RETRIEVAL)
    vector_score_map = {c["chunk_id"]: c["vec_score"] for c in vector_candidates}

    chunk_ids = set(lexical_scores.keys()) | set(vector_score_map.keys())
    candidates = repo.hydrate_candidates(chunk_ids, lexical_scores, vector_score_map)
    return candidates, lexical_ms

def _safe_uuid(value: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def _apply_memory_boosting(
    candidates: list[dict],
    previous_trace_items: list[object],
    max_boost: float = 0.12,
) -> tuple[list[dict], int]:
    boosts_by_key: dict[tuple[str, str], float] = {}
    for rank, item in enumerate(previous_trace_items[:20]):
        try:
            if not bool(getattr(item, "used_in_answer", False)):
                continue
            doc_id = str(getattr(item, "document_id"))
            chunk_id = str(getattr(item, "chunk_id"))
            recency = max(0.3, 1.0 - (rank * 0.2))
            boosts_by_key[(doc_id, chunk_id)] = max(boosts_by_key.get((doc_id, chunk_id), 0.0), max_boost * recency)
        except Exception:  # noqa: BLE001
            continue

    boosted = 0
    updated = []
    for entry in candidates:
        doc_id = str(entry.get("document_id"))
        chunk_id = str(entry.get("chunk_id"))
        boost = min(max_boost, boosts_by_key.get((doc_id, chunk_id), 0.0))
        if boost > 0:
            entry["final_score"] = float(entry.get("final_score", 0.0)) + boost
            entry.setdefault("boosts_applied", []).append({"name": "memory_reuse_boost", "value": boost, "reason": "recent_answer_reuse"})
            boosted += 1
        updated.append(entry)

    updated.sort(key=lambda x: float(x.get("final_score", 0.0)), reverse=True)
    return updated, boosted




def _summarize_metric(name: str) -> MetricSummary:
    samples = metric_samples(name)
    if not samples:
        return MetricSummary(count=0, sum=0.0, avg=0.0, latest=None)
    total = float(sum(samples))
    return MetricSummary(count=len(samples), sum=total, avg=total / len(samples), latest=float(samples[-1]))


def _readiness_db_check(db: Session) -> ReadinessCheck:
    try:
        db.execute(text("SELECT 1"))
        return ReadinessCheck(ok=True)
    except Exception as exc:  # noqa: BLE001
        return ReadinessCheck(ok=False, detail=str(exc))


def _readiness_model_check() -> ReadinessCheck:
    try:
        model_ctx = get_ollama_client().fetch_model_num_ctx(settings.LLM_MODEL)
        if model_ctx is None:
            return ReadinessCheck(ok=False, detail="model metadata unavailable")
        return ReadinessCheck(ok=True, detail=f"num_ctx={model_ctx}")
    except Exception as exc:  # noqa: BLE001
        return ReadinessCheck(ok=False, detail=str(exc))

def _build_retrieval_trace_rows(
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
    ranked_candidates: list[dict],
    chosen_candidates: list[dict],
) -> list[dict]:
    chosen_ids = {str(c.get("chunk_id")) for c in chosen_candidates}
    citation_ranks = {str(c.get("chunk_id")): idx + 1 for idx, c in enumerate(chosen_candidates)}
    rows: list[dict] = []
    for idx, candidate in enumerate(ranked_candidates, start=1):
        doc_id = _safe_uuid(candidate.get("document_id"))
        chunk_id = _safe_uuid(candidate.get("chunk_id"))
        if doc_id is None or chunk_id is None:
            continue
        candidate_id = str(candidate.get("chunk_id"))
        rows.append(
            {
                "conversation_id": conversation_id,
                "turn_id": turn_id,
                "document_id": doc_id,
                "chunk_id": chunk_id,
                "ordinal": idx,
                "score_lex_raw": float(candidate.get("lex_raw", candidate.get("lex_score", 0.0))),
                "score_vec_raw": float(candidate.get("vec_raw", candidate.get("vec_score", 0.0))),
                "score_rerank_raw": float(candidate.get("rerank_raw", candidate.get("rerank_score", 0.0))),
                "score_final": float(candidate.get("final_score", 0.0)),
                "used_in_context": candidate_id in chosen_ids,
                "used_in_answer": candidate_id in chosen_ids,
                "citation_rank": citation_ranks.get(candidate_id),
            }
        )
    return rows



@router.get("/health", response_model=HealthResponse)
@router.get("/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(version=settings.APP_VERSION)


@router.get("/v1/ready", response_model=ReadinessResponse)
@router.get("/ready", response_model=ReadinessResponse)
def ready(db: Session = Depends(get_db)) -> ReadinessResponse:
    request_id = str(uuid.uuid4())
    db_check = _readiness_db_check(db)
    model_check = _readiness_model_check()
    checks = {"db": db_check, "model": model_check}
    all_ok = all(item.ok for item in checks.values())
    logger.info(
        "readiness_check",
        extra={
            "request_id": request_id,
            "stage": "readiness",
            "db_ok": db_check.ok,
            "model_ok": model_check.ok,
        },
    )
    return ReadinessResponse(
        status="ok" if all_ok else "degraded",
        version=settings.APP_VERSION,
        checks=checks,
    )


@router.get("/v1/metrics", response_model=MetricsResponse)
@router.get("/metrics", response_model=MetricsResponse)
def metrics() -> MetricsResponse:
    request_id = str(uuid.uuid4())
    logger.info("metrics_snapshot", extra={"request_id": request_id, "stage": "metrics"})
    return MetricsResponse(
        metrics={
            "token_usage": _summarize_metric("token_usage"),
            "coverage_ratio": _summarize_metric("coverage_ratio"),
            "clarification_rate": _summarize_metric("clarification_rate"),
            "fallback_rate": _summarize_metric("fallback_rate"),
        }
    )


@router.post("/v1/ingest/sources/sync", response_model=JobAcceptedResponse, status_code=202)
def start_source_sync(payload: SourceSyncRequest, db: Session = Depends(get_db)) -> JobAcceptedResponse:
    repo = TenantRepository(db, payload.tenant_id)
    job = repo.create_job(
        job_type="REINDEX_ALL",
        requested_by="api",
        payload={"source_types": payload.source_types, "force_reindex": payload.force_reindex},
    )
    return JobAcceptedResponse(job_id=job.job_id, job_status=job.job_status)


@router.get("/v1/jobs/recent", response_model=JobListResponse)
def get_recent_jobs(tenant_id: uuid.UUID, limit: int = 20, db: Session = Depends(get_db)) -> JobListResponse:
    safe_limit = max(1, min(limit, 100))
    jobs = (
        db.query(IngestJobs)
        .filter(IngestJobs.tenant_id == tenant_id)
        .order_by(IngestJobs.started_at.desc())
        .limit(safe_limit)
        .all()
    )
    return JobListResponse(
        jobs=[
            JobStatusResponse(
                job_id=job.job_id,
                tenant_id=job.tenant_id,
                job_type=job.job_type,
                job_status=job.job_status,
                requested_by=job.requested_by,
                started_at=job.started_at,
                finished_at=job.finished_at,
                error_code=job.error_code,
                error_message=job.error_message,
                result=job.result_json,
            )
            for job in jobs
        ]
    )


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
        finished_at=job.finished_at,
        error_code=job.error_code,
        error_message=job.error_message,
        result=job.result_json,
    )


@router.post("/v1/ingest/files/upload", response_model=JobAcceptedResponse, status_code=202)
async def upload_file_for_ingestion(
    tenant_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> JobAcceptedResponse:
    content = await file.read()
    item = FileByteIngestor().ingest_bytes(filename=file.filename or "upload.bin", payload=content)
    counters = ingest_source_items(db, tenant_id, [item], raw_payloads={item.external_ref: content})
    repo = TenantRepository(db, tenant_id)
    job = repo.create_job(job_type="REINDEX_ALL", requested_by="upload", payload={"source_types": ["FILE_UPLOAD_OBJECT"]})
    repo.mark_job(job, "done", result_payload=counters)
    return JobAcceptedResponse(job_id=job.job_id, job_status=job.job_status)


@router.post("/v1/query", response_model=QueryResponse)
def post_query(
    payload: QueryRequest,
    db: Session = Depends(get_db),
    x_conversation_id: str | None = Header(default=None, alias="X-Conversation-Id"),
    x_client_turn_id: str | None = Header(default=None, alias="X-Client-Turn-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    x_debug_mode: str | None = Header(default=None, alias="X-Debug-Mode"),
) -> QueryResponse:
    corr = uuid.uuid4()
    t_start = time.perf_counter()

    if not rate_limiter.allow(x_user_id or "anonymous"):
        raise _error("RATE_LIMIT_EXCEEDED", "Too many requests. Please retry later.", corr, True, status.HTTP_429_TOO_MANY_REQUESTS)

    debug_requested = (x_debug_mode or "").strip().lower() in {"1", "true", "yes", "on"}
    if debug_requested and not _is_debug_allowed(debug_requested=True, user_role=x_user_role):
        raise _error("DEBUG_FORBIDDEN", "Debug mode is allowed for admin role only", corr, False, status.HTTP_403_FORBIDDEN)
    debug_enabled = _is_plain_log_mode() and _is_debug_allowed(debug_requested=debug_requested, user_role=x_user_role)

    prompt_security = sanitize_user_query(payload.query)
    safe_query = prompt_security.sanitized_query

    safe_payload_log = payload.model_dump()
    safe_payload_log["query"] = safe_query
    log_event(db, str(payload.tenant_id), str(corr), "API_REQUEST", safe_payload_log)
    if prompt_security.malicious_instruction_detected:
        log_event(
            db,
            str(payload.tenant_id),
            str(corr),
            "ERROR",
            {
                "code": "SECURITY_PROMPT_SANITIZED",
                "malicious_instruction_detected": True,
                "stripped_external_tool_directives": prompt_security.stripped_external_tool_directives,
                "stripped_system_override_attempt": prompt_security.stripped_system_override_attempt,
            },
        )

    conversation_repo: ConversationRepository | None = None
    conversation_id: uuid.UUID | None = None
    user_turn_text = safe_query

    if x_conversation_id:
        try:
            conversation_id = uuid.UUID(x_conversation_id)
        except (ValueError, TypeError):
            raise _error("B-CONV-ID-INVALID", "Invalid X-Conversation-Id header", corr, False, status.HTTP_400_BAD_REQUEST)

    if settings.USE_CONVERSATION_MEMORY and conversation_id is not None:
        conversation_repo = ConversationRepository(db, payload.tenant_id)
        conversation = conversation_repo.get_conversation(conversation_id)
        if conversation is None:
            conversation = conversation_repo.create_conversation(conversation_id)
        else:
            ttl_cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.CONVERSATION_TTL_MINUTES)
            last_active_at = conversation.last_active_at
            if last_active_at is not None and last_active_at.tzinfo is None:
                last_active_at = last_active_at.replace(tzinfo=timezone.utc)
            if last_active_at and last_active_at < ttl_cutoff:
                conversation_repo.mark_conversation_archived(conversation)
            conversation_repo.touch_conversation(conversation)

        user_turn_meta = {}
        if x_client_turn_id:
            user_turn_meta["client_turn_id"] = x_client_turn_id
        if not user_turn_meta:
            user_turn_meta = None
        user_turn = conversation_repo.create_turn(conversation_id, "user", user_turn_text, meta=user_turn_meta)
    else:
        user_turn = None

    if conversation_repo is not None and conversation_id is not None:
        recent_turns_for_summary = [
            {"role": t.role, "text": t.text, "turn_index": int(t.turn_index)}
            for t in reversed(conversation_repo.list_turns(conversation_id, limit=max(settings.CONVERSATION_SUMMARY_THRESHOLD_TURNS + 5, 20)))
        ]
        if len(recent_turns_for_summary) >= settings.CONVERSATION_SUMMARY_THRESHOLD_TURNS:
            latest_summary = conversation_repo.get_latest_summary(conversation_id)
            max_turn_index = max([int(t.get("turn_index", 0)) for t in recent_turns_for_summary], default=0)
            covered_index = int(latest_summary.covers_turn_index_to) if latest_summary is not None else 0
            if max_turn_index > covered_index:
                masked_mode = settings.LOG_DATA_MODE.strip().lower() == "masked"
                summary_text_new = get_conversation_summarizer().summarize(recent_turns_for_summary, masked_mode=masked_mode)
                conversation_repo.create_summary(
                    conversation_id=conversation_id,
                    summary_text=summary_text_new,
                    covers_turn_index_to=max_turn_index,
                )

    resolved_query_text = safe_query
    rewrite_result = None
    clarification_enabled = bool(settings.USE_CLARIFICATION_LOOP and settings.USE_LLM_QUERY_REWRITE and settings.USE_CONVERSATION_MEMORY)
    clarification_pending = False
    last_clarification_question: str | None = None
    clarification_depth_for_pipeline = 0
    if conversation_repo is not None and conversation_id is not None:
        latest_resolution = conversation_repo.get_latest_query_resolution(conversation_id)
        if latest_resolution is not None and bool(latest_resolution.needs_clarification):
            clarification_pending = True
            last_clarification_question = latest_resolution.clarification_question

    if settings.USE_LLM_QUERY_REWRITE:
        recent_turns: list[dict] = []
        summary_text: str | None = None
        if conversation_repo is not None and conversation_id is not None:
            recent_turns = [
                {"role": t.role, "text": t.text}
                for t in reversed(conversation_repo.list_turns(conversation_id, limit=settings.CONVERSATION_TURNS_LAST_N))
            ]
            latest_summary = conversation_repo.get_latest_summary(conversation_id)
            summary_text = latest_summary.summary_text if latest_summary else None
        try:
            log_event(
                db,
                str(payload.tenant_id),
                str(corr),
                "LLM_REQUEST",
                {"model": settings.REWRITE_MODEL_ID, "keep_alive": settings.REWRITE_KEEP_ALIVE, "component": "query_rewriter"},
            )
            rewrite_result = get_query_rewriter().rewrite(
                tenant_id=str(payload.tenant_id),
                conversation_id=str(conversation_id) if conversation_id else None,
                user_query=safe_query,
                recent_turns=recent_turns,
                summary=summary_text,
                citation_hints=None,
                clarification_pending=clarification_pending,
                last_question=last_clarification_question,
            )
            resolved_query_text = rewrite_result.resolved_query_text
            log_event(
                db,
                str(payload.tenant_id),
                str(corr),
                "LLM_RESPONSE",
                {"model": settings.REWRITE_MODEL_ID, "keep_alive": settings.REWRITE_KEEP_ALIVE, "component": "query_rewriter", "confidence": rewrite_result.confidence},
            )
            if settings.ENABLE_PER_STAGE_LATENCY_METRICS:
                rewrite_ms = int((time.perf_counter() - t_start) * 1000)
                log_stage_latency(stage="rewrite_agent", latency_ms=rewrite_ms, model_id=settings.REWRITE_MODEL_ID, request_id=str(corr))
                emit_metric("rag_rewrite_latency", rewrite_ms)
        except (QueryRewriteError, ValueError, KeyError, json.JSONDecodeError) as exc:
            log_event(db, str(payload.tenant_id), str(corr), "ERROR", {"code": "B-REWRITE-FAILED", "message": str(exc)})
            raise _error("B-REWRITE-FAILED", "Query rewrite failed", corr, True, status.HTTP_502_BAD_GATEWAY)

        if conversation_repo is not None and conversation_id is not None and user_turn is not None:
            conversation_repo.create_query_resolution(
                conversation_id=conversation_id,
                turn_id=user_turn.turn_id,
                resolved_query_text=rewrite_result.resolved_query_text,
                rewrite_strategy="llm_rewrite",
                rewrite_inputs={
                    "recent_turns_count": len(recent_turns),
                    "has_summary": bool(summary_text),
                    "rewrite_model_id": settings.REWRITE_MODEL_ID,
                    "rewrite_keep_alive": settings.REWRITE_KEEP_ALIVE,
                    "clarification_pending": clarification_pending,
                    "last_question": last_clarification_question,
                    "clarification_depth": conversation_repo.count_recent_consecutive_clarifications(conversation_id),
                },
                rewrite_confidence=rewrite_result.confidence,
                topic_shift_detected=rewrite_result.topic_shift,
                needs_clarification=rewrite_result.clarification_needed,
                clarification_question=rewrite_result.clarification_question,
            )

        if clarification_enabled and conversation_repo is not None and conversation_id is not None and user_turn is not None:
            clarification_streak = conversation_repo.count_recent_consecutive_clarifications(conversation_id)
            clarification_depth = clarification_streak + (1 if rewrite_result and rewrite_result.clarification_needed else 0)
            clarification_depth_for_pipeline = clarification_depth
            should_ask = bool(rewrite_result and rewrite_result.clarification_needed and rewrite_result.confidence < settings.REWRITE_CONFIDENCE_THRESHOLD)
            if should_ask:
                pipeline = get_agent_pipeline()
                pipeline_result = pipeline.run(
                    AgentPipelineRequest(
                        query=safe_query,
                        rewrite_input=RewriteAgentInput(
                            query=safe_query,
                            execute=lambda _q: {
                                "resolved_query_text": resolved_query_text,
                                "clarification_needed": bool(rewrite_result and rewrite_result.clarification_needed),
                                "clarification_question": rewrite_result.clarification_question if rewrite_result else None,
                                "confidence": float(rewrite_result.confidence) if rewrite_result else 1.0,
                            },
                        ),
                        retrieval_input=RetrievalAgentInput(query=resolved_query_text, execute=lambda _q: {"ranked_candidates": []}),
                        analysis_input_builder=lambda ranked_candidates: AnalysisAgentInput(
                            ranked_candidates=ranked_candidates,
                            execute=lambda _items: {"selected_candidates": [], "confidence": 0.0},
                        ),
                        answer_input_builder=lambda selected_candidates: AnswerAgentInput(
                            query=safe_query,
                            selected_candidates=selected_candidates,
                            execute=lambda _q, _selected: {"answer": "", "only_sources_verdict": "PASS"},
                        ),
                        max_clarification_depth=settings.MAX_CLARIFICATION_DEPTH,
                        clarification_depth=clarification_depth,
                        confidence_fallback_threshold=-1.0,
                        debug=debug_enabled,
                    )
                )

                if pipeline_result.fallback_reason == "clarification_depth_exceeded":
                    log_event(db, str(payload.tenant_id), str(corr), "ERROR", {"code": "RH-CLARIFICATION-DEPTH-EXCEEDED", "clarification_depth": clarification_depth, "max_clarification_depth": settings.MAX_CLARIFICATION_DEPTH})

                if debug_enabled:
                    log_event(
                        db,
                        str(payload.tenant_id),
                        str(corr),
                        "PIPELINE_STAGE",
                        {
                            "agent_trace": [
                                {"stage": t.stage, "latency_ms": t.latency_ms, "output": t.output}
                                for t in pipeline_result.stage_traces
                            ]
                        },
                    )

                assistant_meta = {"correlation_id": str(corr), "clarification_depth": clarification_depth}
                if pipeline_result.needs_clarification:
                    assistant_meta["clarification"] = True
                if pipeline_result.fallback_reason == "clarification_depth_exceeded":
                    assistant_meta["clarification_limit_exceeded"] = True

                conversation_repo.create_turn(conversation_id, "assistant", pipeline_result.answer, meta=assistant_meta)
                t_total_ms = int((time.perf_counter() - t_start) * 1000)
                trace = {"trace_id": str(corr), "scoring_trace": []}
                log_event(db, str(payload.tenant_id), str(corr), "API_RESPONSE", trace, duration_ms=t_total_ms)
                return QueryResponse(
                    answer=pipeline_result.answer,
                    only_sources_verdict=pipeline_result.only_sources_verdict,
                    citations=[],
                    correlation_id=corr,
                    trace={"trace_id": corr, "scoring_trace": []},
                )

            elif should_ask and clarification_streak >= settings.MAX_CLARIFICATION_DEPTH:
                fallback_message = "Похоже, недостаточно информации для ответа... Попробуйте уточнить вопрос и сузить область поиска."
                log_event(db, str(payload.tenant_id), str(corr), "ERROR", {"code": "RH-CLARIFICATION-DEPTH-EXCEEDED", "clarification_depth": clarification_streak, "max_clarification_depth": settings.MAX_CLARIFICATION_DEPTH})
                conversation_repo.create_turn(conversation_id, "assistant", fallback_message, meta={"correlation_id": str(corr), "clarification_limit_exceeded": True})
                return QueryResponse(
                    answer=fallback_message,
                    only_sources_verdict="FAIL",
                    citations=[],
                    correlation_id=corr,
                    trace={"trace_id": corr, "scoring_trace": []},
                )

    try:
        log_event(db, str(payload.tenant_id), str(corr), "EMBEDDINGS_REQUEST", {"query": resolved_query_text, "model": settings.EMBEDDINGS_DEFAULT_MODEL_ID})
        query_embedding = get_embeddings_client().embed_text(resolved_query_text, tenant_id=str(payload.tenant_id), correlation_id=str(corr))
        log_event(db, str(payload.tenant_id), str(corr), "EMBEDDINGS_RESPONSE", {"dimensions": len(query_embedding)})
    except Exception as exc:  # noqa: BLE001
        log_event(db, str(payload.tenant_id), str(corr), "ERROR", {"code": "EMBEDDINGS_HTTP_ERROR", "message": str(exc)})
        raise _error("EMBEDDINGS_HTTP_ERROR", "Embeddings service call failed", corr, True, status.HTTP_500_INTERNAL_SERVER_ERROR)

    t_parse0 = time.perf_counter()
    candidates, lexical_ms = _fetch_candidates(db, str(payload.tenant_id), resolved_query_text, query_embedding, max(payload.top_k, settings.RERANKER_TOP_K))
    t_parse_ms = int((time.perf_counter() - t_parse0) * 1000)
    if settings.ENABLE_PER_STAGE_LATENCY_METRICS:
        log_stage_latency(stage="retrieval_agent", latency_ms=t_parse_ms, model_id=settings.EMBEDDINGS_DEFAULT_MODEL_ID, request_id=str(corr))
        emit_metric("rag_retrieval_latency", t_parse_ms)

    ranked, timers = hybrid_rank(
        resolved_query_text,
        candidates,
        query_embedding,
        normalize_scores=settings.HYBRID_SCORE_NORMALIZATION,
    )
    reranked, t_rerank = get_reranker().rerank(resolved_query_text, ranked)
    ranked_final, _ = hybrid_rank(
        resolved_query_text,
        reranked,
        query_embedding,
        normalize_scores=settings.HYBRID_SCORE_NORMALIZATION,
    )

    boosted_chunks_count = 0
    if conversation_repo is not None and conversation_id is not None and user_turn is not None:
        previous_trace = conversation_repo.list_retrieval_trace_items(conversation_id, limit=50)
        ranked_final, boosted_chunks_count = _apply_memory_boosting(ranked_final, previous_trace)

    tenant_safe_ranked = [c for c in ranked_final if c.get("tenant_id") == str(payload.tenant_id)]
    chosen = expand_neighbors(
        db,
        str(payload.tenant_id),
        tenant_safe_ranked,
        payload.top_k,
        use_contextual_expansion=settings.USE_CONTEXTUAL_EXPANSION,
        neighbor_window=settings.NEIGHBOR_WINDOW,
    )
    chosen, budget_log = apply_context_budget(
        chosen,
        use_token_budget_assembly=settings.USE_TOKEN_BUDGET_ASSEMBLY,
        max_context_tokens=settings.MAX_CONTEXT_TOKENS,
    )

    only_sources = "PASS"
    anti_payload = {"refusal_triggered": False, "unsupported_sentences": 0}
    t_llm_ms = 0
    llm_tokens_est = 0
    llm_completion_tokens_est = 0

    if not chosen:
        answer = build_structured_refusal(str(corr), {"reason": "no_sources"})
        anti_payload = {"refusal_triggered": True, "unsupported_sentences": 0}
        only_sources = "FAIL"
    elif not settings.USE_LLM_GENERATION:
        answer = _build_retrieval_only_answer(chosen)
    else:
        prompt = _build_llm_prompt(safe_query, chosen)
        llm_tokens_est = _estimate_token_count(prompt)
        llm_start = time.perf_counter()
        try:
            request_log_payload = {"model": settings.LLM_MODEL, "keep_alive": settings.OLLAMA_KEEP_ALIVE_SECONDS, "num_ctx": settings.LLM_NUM_CTX, "prompt_tokens_est": llm_tokens_est}
            if _is_plain_log_mode():
                request_log_payload["prompt"] = prompt
            log_event(db, str(payload.tenant_id), str(corr), "LLM_REQUEST", request_log_payload)
            llm_payload = get_ollama_client().generate(prompt, keep_alive=settings.OLLAMA_KEEP_ALIVE_SECONDS)
            if isinstance(llm_payload, dict):
                llm_raw = str(llm_payload.get("response", ""))
            else:
                llm_raw = str(llm_payload)
            llm_completion_tokens_est = _estimate_token_count(llm_raw)
            response_log_payload = {
                "model": settings.LLM_MODEL,
                "keep_alive": settings.OLLAMA_KEEP_ALIVE_SECONDS,
                "num_ctx": settings.LLM_NUM_CTX,
                "completion_tokens_est": llm_completion_tokens_est,
            }
            if _is_plain_log_mode():
                response_log_payload["raw"] = llm_payload
            log_event(db, str(payload.tenant_id), str(corr), "LLM_RESPONSE", response_log_payload)
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

    if settings.ENABLE_PER_STAGE_LATENCY_METRICS:
        analysis_ms = int(timers.get("t_vector_ms", 0) + t_rerank)
        log_stage_latency(stage="analysis_agent", latency_ms=analysis_ms, model_id=settings.RERANKER_MODEL, request_id=str(corr))
        emit_metric("rag_analysis_latency", analysis_ms)
        log_stage_latency(stage="answer_agent", latency_ms=t_llm_ms if t_llm_ms > 0 else t_citations_ms, model_id=settings.LLM_MODEL, request_id=str(corr))
        emit_metric("rag_answer_latency", t_llm_ms if t_llm_ms > 0 else t_citations_ms)
    t_total_ms = int((time.perf_counter() - t_start) * 1000)
    perf = {
        "t_parse_ms": t_parse_ms,
        **timers,
        "t_lexical_ms": lexical_ms,
        "t_rerank_ms": t_rerank,
        "t_total_ms": t_total_ms,
        "t_llm_ms": t_llm_ms,
        "t_citations_ms": t_citations_ms,
        "llm_prompt_tokens_est": llm_tokens_est,
        "llm_completion_tokens_est": llm_completion_tokens_est,
        **budget_log,
        "boosted_chunks_count": boosted_chunks_count,
    }
    budgets = build_stage_budgets(settings.REQUEST_TIMEOUT_SECONDS, settings.EMBEDDINGS_TIMEOUT_SECONDS)
    exceeded = exceeded_budgets(perf, budgets)
    if exceeded:
        log_event(db, str(payload.tenant_id), str(corr), "ERROR", {"message": "perf_budget_exceeded", "exceeded": exceeded, "perf": perf, "budgets": budgets})

    response_confidence = 1.0
    if settings.USE_LLM_GENERATION:
        response_confidence = float(chosen[0].get("final_score", 0.0) or 0.0) if chosen else 0.0

    pipeline = get_agent_pipeline()
    pipeline_result = pipeline.run(
        AgentPipelineRequest(
            query=safe_query,
            rewrite_input=RewriteAgentInput(
                query=safe_query,
                execute=lambda _q: {
                    "resolved_query_text": resolved_query_text,
                    "clarification_needed": bool(rewrite_result and rewrite_result.clarification_needed),
                    "clarification_question": rewrite_result.clarification_question if rewrite_result else None,
                    "confidence": float(rewrite_result.confidence) if rewrite_result else 1.0,
                },
            ),
            retrieval_input=RetrievalAgentInput(query=resolved_query_text, execute=lambda _q: {"ranked_candidates": tenant_safe_ranked}),
            analysis_input_builder=lambda ranked_candidates: AnalysisAgentInput(
                ranked_candidates=ranked_candidates,
                execute=lambda _items: {"selected_candidates": chosen, "confidence": response_confidence},
            ),
            answer_input_builder=lambda selected_candidates: AnswerAgentInput(
                query=safe_query,
                selected_candidates=selected_candidates,
                execute=lambda _q, _selected: {"answer": answer, "only_sources_verdict": only_sources},
            ),
            max_clarification_depth=settings.MAX_CLARIFICATION_DEPTH,
            clarification_depth=clarification_depth_for_pipeline,
            confidence_fallback_threshold=settings.CONFIDENCE_FALLBACK_THRESHOLD if settings.USE_LLM_GENERATION else -1.0,
            debug=debug_enabled,
        )
    )
    answer = pipeline_result.answer
    only_sources = pipeline_result.only_sources_verdict
    response_confidence = pipeline_result.confidence

    selected_candidates_final = pipeline_result.selected_candidates
    coverage_ratio = (len(selected_candidates_final) / len(tenant_safe_ranked)) if tenant_safe_ranked else 0.0
    clarification_rate = 1.0 if pipeline_result.needs_clarification else 0.0
    fallback_rate = 1.0 if only_sources != "PASS" else 0.0
    emit_metric("token_usage", float(llm_tokens_est + llm_completion_tokens_est))
    emit_metric("coverage_ratio", float(coverage_ratio))
    emit_metric("clarification_rate", clarification_rate)
    emit_metric("fallback_rate", fallback_rate)
    if debug_enabled:
        log_event(
            db,
            str(payload.tenant_id),
            str(corr),
            "PIPELINE_STAGE",
            {
                "agent_trace": [
                    {"stage": t.stage, "latency_ms": t.latency_ms, "output": t.output}
                    for t in pipeline_result.stage_traces
                ]
            },
        )

    trace = build_scoring_trace(str(corr), chosen)
    trace["anti_hallucination"] = anti_payload
    trace["timing"] = perf
    trace["confidence"] = response_confidence

    if conversation_repo is not None and conversation_id is not None and user_turn is not None:
        trace_rows = _build_retrieval_trace_rows(conversation_id, user_turn.turn_id, tenant_safe_ranked, chosen)
        conversation_repo.create_retrieval_trace_items(trace_rows)

    log_event(db, str(payload.tenant_id), str(corr), "PIPELINE_STAGE", {"stage": "FUSION_BOOST", "trace_id": trace["trace_id"], "scoring_trace": trace["scoring_trace"], "timing": perf})
    log_event(db, str(payload.tenant_id), str(corr), "API_RESPONSE", trace, duration_ms=t_total_ms)
    if conversation_repo is not None and conversation_id is not None:
        conversation_repo.create_turn(conversation_id, "assistant", answer, meta={"correlation_id": str(corr)})

    return QueryResponse(
        answer=answer,
        only_sources_verdict=only_sources,
        citations=citations if payload.citations else [],
        correlation_id=corr,
        trace={"trace_id": corr, "scoring_trace": trace["scoring_trace"]},
    )
