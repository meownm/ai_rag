from __future__ import annotations

from os import getenv

MAX_CONTEXT_WORDS = 12000
DEFAULT_TOP_K = int(getenv("DEFAULT_TOP_K", "5"))
USE_CONTEXTUAL_EXPANSION = getenv("USE_CONTEXTUAL_EXPANSION", "false").lower() == "true"
NEIGHBOR_WINDOW = int(getenv("NEIGHBOR_WINDOW", "1"))
USE_TOKEN_BUDGET_ASSEMBLY = getenv("USE_TOKEN_BUDGET_ASSEMBLY", "false").lower() == "true"
MAX_CONTEXT_TOKENS = int(getenv("MAX_CONTEXT_TOKENS", "8000"))
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
    if not use_token_budget_assembly:
        before = sum(token_count(c["chunk_text"]) for c in chunks)
        if before <= max_context_words:
            return chunks, {
                "context_word_count_before": before,
                "context_word_count_after": before,
                "chunks_dropped_count": 0,
                "total_context_tokens_est": sum(estimate_tokens(c["chunk_text"]) for c in chunks),
                "max_context_tokens": max_context_tokens,
                "truncated": False,
            }

        retained = list(chunks)
        dropped = 0
        while retained and sum(token_count(c["chunk_text"]) for c in retained) > max_context_words:
            idx = min(
                range(len(retained)),
                key=lambda i: (
                    float(retained[i].get("final_score", 0.0)),
                    retained[i].get("rank_position", 9999),
                    retained[i]["chunk_id"],
                ),
            )
            retained.pop(idx)
            dropped += 1
        after = sum(token_count(c["chunk_text"]) for c in retained)
        return retained, {
            "context_word_count_before": before,
            "context_word_count_after": after,
            "chunks_dropped_count": dropped,
            "total_context_tokens_est": sum(estimate_tokens(c["chunk_text"]) for c in retained),
            "max_context_tokens": max_context_tokens,
            "truncated": False,
        }

    if not chunks:
        return [], {
            "context_word_count_before": 0,
            "context_word_count_after": 0,
            "chunks_dropped_count": 0,
            "total_context_tokens_est": 0,
            "max_context_tokens": max_context_tokens,
            "truncated": False,
        }

    assembled: list[dict] = []
    dropped = 0
    total_tokens = 0
    truncated = False

    for idx, chunk in enumerate(chunks):
        text = str(chunk.get("chunk_text", ""))
        chunk_tokens = estimate_tokens(text)

        if idx == 0 and chunk_tokens > max_context_tokens:
            truncated_chunk = dict(chunk)
            truncated_chunk["chunk_text"] = _truncate_text_to_tokens(text, max_context_tokens)
            truncated_chunk["context_truncated"] = True
            assembled = [truncated_chunk]
            total_tokens = estimate_tokens(truncated_chunk["chunk_text"])
            dropped = max(0, len(chunks) - 1)
            truncated = True
            break

        if total_tokens + chunk_tokens <= max_context_tokens:
            assembled.append(chunk)
            total_tokens += chunk_tokens
        else:
            dropped += 1

    if not assembled:
        assembled = [chunks[0]]
        total_tokens = estimate_tokens(str(chunks[0].get("chunk_text", "")))

    before_words = sum(token_count(c.get("chunk_text", "")) for c in chunks)
    after_words = sum(token_count(c.get("chunk_text", "")) for c in assembled)
    return assembled, {
        "context_word_count_before": before_words,
        "context_word_count_after": after_words,
        "chunks_dropped_count": dropped,
        "total_context_tokens_est": total_tokens,
        "max_context_tokens": max_context_tokens,
        "truncated": truncated,
    }
