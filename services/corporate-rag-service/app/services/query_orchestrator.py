"""High-level query orchestration extracted from routes.post_query."""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.clients.embeddings_client import EmbeddingsClient
from app.clients.ollama_client import OllamaClient
from app.core.config import settings
from app.core.token_utils import estimate_tokens
from app.db.repositories import TenantRepository
from app.services.anti_hallucination import build_structured_refusal, verify_answer
from app.services.context_expansion import ContextExpansionEngine
from app.services.query_pipeline import apply_context_budget, expand_neighbors
from app.services.reranker import RerankerService
from app.services.retrieval import hybrid_rank
from app.services.security import PromptSecurityResult, sanitize_user_query


@dataclass
class QueryResult:
    """Value object returned by QueryOrchestrator.execute()."""
    answer: str
    only_sources_verdict: str
    citations: list[dict]
    chosen_candidates: list[dict]
    ranked_candidates: list[dict]
    timing: dict[str, Any] = field(default_factory=dict)
    budget_log: dict[str, Any] = field(default_factory=dict)
    expansion_debug: dict[str, Any] = field(default_factory=dict)
    anti_hallucination_payload: dict[str, Any] = field(default_factory=dict)
    prompt_security: PromptSecurityResult | None = None
    resolved_query_text: str = ""
    response_confidence: float = 1.0
    llm_tokens_est: int = 0
    llm_completion_tokens_est: int = 0
    boosted_chunks_count: int = 0


class QueryOrchestrator:
    """Orchestrates the full RAG query pipeline: embed -> retrieve -> rank -> rerank -> expand -> generate -> validate."""

    def __init__(
        self,
        db: Session,
        tenant_id: str,
        embeddings_client: EmbeddingsClient,
        reranker: RerankerService,
        ollama_client: OllamaClient,
        correlation_id: uuid.UUID,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.embeddings_client = embeddings_client
        self.reranker = reranker
        self.ollama_client = ollama_client
        self.corr = correlation_id

    def sanitize(self, query: str) -> PromptSecurityResult:
        return sanitize_user_query(query)

    def embed_query(self, query: str) -> list[float]:
        return self.embeddings_client.embed_text(
            query,
            tenant_id=self.tenant_id,
            correlation_id=str(self.corr),
        )

    def fetch_and_rank(
        self,
        query: str,
        query_embedding: list[float],
        top_k: int,
    ) -> tuple[list[dict], dict[str, Any]]:
        """Retrieve candidates, hybrid-rank, rerank, and re-rank."""
        repo = TenantRepository(self.db, self.tenant_id)
        k_lex = max(top_k, settings.DEFAULT_TOP_K, settings.HYBRID_MAX_FTS)
        k_vec = max(top_k, settings.RERANKER_TOP_K, settings.HYBRID_MAX_VECTOR)

        t0 = time.perf_counter()
        lexical_scores = repo.fetch_lexical_candidate_scores(query, k_lex)
        lexical_ms = int((time.perf_counter() - t0) * 1000)
        vector_candidates = repo.fetch_vector_candidates(
            query_embedding, k_vec, use_similarity=settings.USE_VECTOR_RETRIEVAL,
        )
        vector_score_map = {c["chunk_id"]: c["vec_score"] for c in vector_candidates}

        chunk_ids = set(lexical_scores.keys()) | set(vector_score_map.keys())
        candidates = repo.hydrate_candidates(chunk_ids, lexical_scores, vector_score_map)

        ranked, timers = hybrid_rank(
            query, candidates, query_embedding,
            normalize_scores=settings.HYBRID_SCORE_NORMALIZATION,
        )
        reranked, t_rerank = self.reranker.rerank(query, ranked)
        ranked_final, _ = hybrid_rank(
            query, reranked, query_embedding,
            normalize_scores=settings.HYBRID_SCORE_NORMALIZATION,
        )

        # Tenant-safety filter
        ranked_final = [c for c in ranked_final if c.get("tenant_id") == self.tenant_id]

        timing = {
            **timers,
            "t_lexical_ms": lexical_ms,
            "t_rerank_ms": t_rerank,
            "lexical_count": len(lexical_scores),
            "vector_count": len(vector_candidates),
        }
        return ranked_final, timing

    def expand_context(
        self,
        ranked: list[dict],
        top_k: int,
        query_embedding: list[float],
        resolved_query: str,
    ) -> tuple[list[dict], dict[str, Any], dict[str, int]]:
        """Apply context expansion and token budget."""
        chosen = expand_neighbors(
            self.db,
            self.tenant_id,
            ranked,
            top_k,
            use_contextual_expansion=settings.USE_CONTEXTUAL_EXPANSION,
            neighbor_window=settings.NEIGHBOR_WINDOW,
        )
        expansion_debug: dict[str, Any] = {
            "base_topk_count": min(len(ranked), top_k),
            "base_candidates_doc_diversity": len({str(c.get("document_id")) for c in ranked[:top_k]}),
            "expanded_chunks_count": len(chosen),
            "expanded_from_neighbors_count": sum(1 for c in chosen if c.get("added_by_neighbor")),
            "expanded_from_links_count": 0,
            "redundancy_filtered_count": 0,
            "final_context_token_estimate": sum(estimate_tokens(str(c.get("chunk_text", ""))) for c in chosen),
            "context_selection_steps": ["legacy_expand_neighbors"],
        }
        expansion_timing: dict[str, int] = {"selection_ms": 0, "budget_ms": 0}

        mode = settings.CONTEXT_EXPANSION_MODE.strip().lower()
        expansion_enabled = settings.CONTEXT_EXPANSION_ENABLED and mode != "off"
        if expansion_enabled:
            t_expand0 = time.perf_counter()
            engine = ContextExpansionEngine(TenantRepository(self.db, self.tenant_id))
            chosen, debug_info = engine.expand(
                final_query=resolved_query,
                base_candidates=ranked,
                token_budget=settings.MAX_CONTEXT_TOKENS,
                mode=mode,
                query_embedding=query_embedding,
            )
            expansion_debug = {
                "base_topk_count": debug_info.base_topk_count,
                "base_candidates_doc_diversity": debug_info.base_candidates_doc_diversity,
                "expanded_chunks_count": debug_info.expanded_chunks_count,
                "expanded_from_neighbors_count": debug_info.expanded_from_neighbors_count,
                "expanded_from_links_count": debug_info.expanded_from_links_count,
                "redundancy_filtered_count": debug_info.redundancy_filtered_count,
                "final_context_token_estimate": debug_info.final_context_token_estimate,
                "context_selection_steps": debug_info.context_selection_steps,
                "expanded_total": debug_info.expanded_total,
                "expanded_per_doc": debug_info.expanded_per_doc,
            }
            expansion_timing["selection_ms"] = int((time.perf_counter() - t_expand0) * 1000)

        t_budget0 = time.perf_counter()
        chosen, budget_log = apply_context_budget(
            chosen,
            use_token_budget_assembly=settings.USE_TOKEN_BUDGET_ASSEMBLY,
            max_context_tokens=settings.MAX_CONTEXT_TOKENS,
        )
        expansion_timing["budget_ms"] = int((time.perf_counter() - t_budget0) * 1000)
        expansion_debug["final_context_token_estimate"] = int(budget_log.get("total_context_tokens_est", 0))

        return chosen, expansion_debug, expansion_timing

    def generate_answer(
        self,
        query: str,
        chosen: list[dict],
    ) -> tuple[str, str, dict[str, Any], int, int]:
        """Generate an answer via LLM or retrieval-only fallback.

        Returns (answer, only_sources_verdict, anti_payload, llm_tokens_est, llm_completion_tokens_est).
        """
        if not chosen:
            return (
                build_structured_refusal(str(self.corr), {"reason": "no_sources"}),
                "FAIL",
                {"refusal_triggered": True, "unsupported_sentences": 0},
                0,
                0,
            )

        if not settings.USE_LLM_GENERATION:
            selected = [c.get("chunk_text", "").strip() for c in chosen[:2] if c.get("chunk_text", "").strip()]
            return "\n\n".join(selected), "PASS", {"refusal_triggered": False, "unsupported_sentences": 0}, 0, 0

        prompt = _build_llm_prompt(query, chosen)
        prompt_tokens = estimate_tokens(prompt)
        max_prompt_tokens = max(1, int(settings.LLM_NUM_CTX) - int(settings.TOKEN_BUDGET_SAFETY_MARGIN))
        if prompt_tokens > max_prompt_tokens:
            raise TokenBudgetExceeded("Assembled prompt exceeds context window")

        llm_start = time.perf_counter()
        try:
            llm_payload = self.ollama_client.generate(prompt, keep_alive=settings.OLLAMA_KEEP_ALIVE_SECONDS)
            llm_raw = str(llm_payload.get("response", "")) if isinstance(llm_payload, dict) else str(llm_payload)
        except Exception:  # noqa: BLE001
            llm_raw = ""
        llm_completion_tokens = estimate_tokens(llm_raw)
        t_llm_ms = int((time.perf_counter() - llm_start) * 1000)

        parsed = _extract_json_payload(llm_raw)
        citations_from_model = parsed.get("citations") if isinstance(parsed, dict) else None
        allowed_pairs = {(str(c.get("chunk_id")), str(c.get("document_id"))) for c in chosen}
        grounded_citations, _stripped = _ground_citations(citations_from_model, allowed_pairs)

        if parsed.get("status") != "success":
            return (
                build_structured_refusal(str(self.corr), {"reason": "insufficient_evidence", "raw": llm_raw}),
                "FAIL",
                {"refusal_triggered": True, "unsupported_sentences": 0},
                prompt_tokens,
                llm_completion_tokens,
            )

        answer = str(parsed.get("answer", "")).strip()
        valid, anti_payload = verify_answer(
            answer,
            [c["chunk_text"] for c in chosen],
            settings.MIN_SENTENCE_SIMILARITY,
            settings.MIN_LEXICAL_OVERLAP,
        )
        if not valid or not answer:
            return (
                build_structured_refusal(str(self.corr), anti_payload),
                "FAIL",
                anti_payload,
                prompt_tokens,
                llm_completion_tokens,
            )

        return answer, "PASS", anti_payload, prompt_tokens, llm_completion_tokens

    def build_citations(self, chosen: list[dict]) -> list[dict]:
        return [
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


class TokenBudgetExceeded(ValueError):
    """Raised when the assembled prompt exceeds the LLM context window."""


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
        '{"status":"success","answer":"...","citations":[{"chunk_id":"...","document_id":"...","quote":"..."}]}'
        "\nIf evidence is insufficient return:\n"
        '{"status":"insufficient_evidence","message":"..."}'
        f"\nQuestion: {query}\n\nContext:\n{blocks}"
    )


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


def _ground_citations(
    citations_from_model: object,
    allowed_pairs: set[tuple[str, str]],
) -> tuple[list[dict], bool]:
    if not isinstance(citations_from_model, list):
        return [], True
    grounded: list[dict] = []
    removed = False
    for citation in citations_from_model:
        if not isinstance(citation, dict):
            removed = True
            continue
        pair = (str(citation.get("chunk_id")), str(citation.get("document_id")))
        if pair in allowed_pairs:
            grounded.append(citation)
        else:
            removed = True
    return grounded, removed
