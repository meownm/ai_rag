from __future__ import annotations

from app.core.config import settings

MAX_CONTEXT_WORDS = 12000
DEFAULT_TOP_K = settings.DEFAULT_TOP_K
USE_CONTEXTUAL_EXPANSION = settings.USE_CONTEXTUAL_EXPANSION
NEIGHBOR_WINDOW = settings.NEIGHBOR_WINDOW
USE_TOKEN_BUDGET_ASSEMBLY = settings.USE_TOKEN_BUDGET_ASSEMBLY
MAX_CONTEXT_TOKENS = settings.MAX_CONTEXT_TOKENS
TRUNCATION_MARKER = "\n[TRUNCATED_BY_TOKEN_BUDGET]"


def token_count(text: str) -> int:
    return len([t for t in text.split() if t])


def _tiktoken_estimate(text: str) -> int:
    import tiktoken  # type: ignore

    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def estimate_tokens(text: str) -> int:
    try:
        return _tiktoken_estimate(text)
    except Exception:  # noqa: BLE001
        words = token_count(text)
        return int(max(1, round(words * 1.33)))


def _truncate_text_to_tokens(text: str, budget_tokens: int) -> str:
    if budget_tokens <= 0:
        return TRUNCATION_MARKER

    words = text.split()
    if not words:
        return TRUNCATION_MARKER

    approx_words_budget = max(1, int(budget_tokens / 1.33))
    truncated = " ".join(words[:approx_words_budget])
    return f"{truncated}{TRUNCATION_MARKER}"


def expand_neighbors(
    db,
    tenant_id: str,
    top_chunks: list[dict],
    top_k: int,
    use_contextual_expansion: bool = USE_CONTEXTUAL_EXPANSION,
    neighbor_window: int = NEIGHBOR_WINDOW,
) -> list[dict]:
    from app.db.repositories import TenantRepository

    base = top_chunks[:top_k]
    if not use_contextual_expansion:
        return base

    cap = min(12, max(top_k, DEFAULT_TOP_K) * 3)
    neighbors = TenantRepository(db, tenant_id).fetch_neighbors(base, max(0, cap - len(base)), window=max(1, neighbor_window))
    expanded: list[dict] = []
    seen: set[str] = set()
    merged = [*base, *neighbors]
    merged = sorted(merged, key=lambda c: (str(c.get("document_id")), int(c.get("ordinal", 0)), str(c.get("chunk_id"))))

    for c in merged:
        cid = str(c["chunk_id"])
        if cid in seen or len(expanded) >= cap:
            continue
        seen.add(cid)
        expanded.append(c)
    return expanded


def apply_context_budget(
    chunks: list[dict],
    max_context_words: int = MAX_CONTEXT_WORDS,
    use_token_budget_assembly: bool = USE_TOKEN_BUDGET_ASSEMBLY,
    max_context_tokens: int = MAX_CONTEXT_TOKENS,
) -> tuple[list[dict], dict]:
    _ = max_context_words
    if not use_token_budget_assembly:
        raise ValueError("Word-based context trimming is no longer supported; enable token budget assembly")

    effective_budget = max(0, int(max_context_tokens) - int(settings.TOKEN_BUDGET_SAFETY_MARGIN))

    if not chunks:
        return [], {
            "context_word_count_before": 0,
            "context_word_count_after": 0,
            "chunks_dropped_count": 0,
            "total_context_tokens_est": 0,
            "max_context_tokens": max_context_tokens,
            "effective_context_tokens": effective_budget,
            "truncated": False,
            "initial_tokens": 0,
            "trimmed_tokens": 0,
            "final_tokens": 0,
        }

    assembled = [dict(chunk) for chunk in chunks]
    token_map = {str(c.get("chunk_id")): estimate_tokens(str(c.get("chunk_text", ""))) for c in assembled}
    initial_tokens = sum(token_map.values())

    dropped = 0
    truncated = False

    # Deterministic low-score trimming first.
    while assembled and sum(token_map[str(c.get("chunk_id"))] for c in assembled) > effective_budget:
        removable = sorted(
            assembled,
            key=lambda c: (
                float(c.get("final_score", 0.0)),
                str(c.get("chunk_id")),
            ),
        )[0]
        assembled = [c for c in assembled if str(c.get("chunk_id")) != str(removable.get("chunk_id"))]
        dropped += 1

    if not assembled:
        best = dict(sorted(chunks, key=lambda c: (-float(c.get("final_score", 0.0)), str(c.get("chunk_id"))))[0])
        best["chunk_text"] = _truncate_text_to_tokens(str(best.get("chunk_text", "")), effective_budget)
        best["context_truncated"] = True
        assembled = [best]
        truncated = True

    final_tokens = sum(estimate_tokens(str(c.get("chunk_text", ""))) for c in assembled)
    if final_tokens > effective_budget and assembled:
        tail = dict(assembled[-1])
        keep = max(1, effective_budget - sum(estimate_tokens(str(c.get("chunk_text", ""))) for c in assembled[:-1]))
        tail["chunk_text"] = _truncate_text_to_tokens(str(tail.get("chunk_text", "")), keep)
        tail["context_truncated"] = True
        assembled[-1] = tail
        truncated = True
        final_tokens = sum(estimate_tokens(str(c.get("chunk_text", ""))) for c in assembled)
    trimmed_tokens = max(0, initial_tokens - final_tokens)

    before_words = sum(token_count(c.get("chunk_text", "")) for c in chunks)
    after_words = sum(token_count(c.get("chunk_text", "")) for c in assembled)
    return assembled, {
        "context_word_count_before": before_words,
        "context_word_count_after": after_words,
        "chunks_dropped_count": dropped,
        "total_context_tokens_est": final_tokens,
        "max_context_tokens": max_context_tokens,
        "effective_context_tokens": effective_budget,
        "truncated": truncated,
        "initial_tokens": initial_tokens,
        "trimmed_tokens": trimmed_tokens,
        "final_tokens": final_tokens,
    }
