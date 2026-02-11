from os import getenv

MAX_CONTEXT_WORDS = 12000
DEFAULT_TOP_K = int(getenv("DEFAULT_TOP_K", "5"))


def token_count(text: str) -> int:
    return len([t for t in text.split() if t])


def expand_neighbors(db, tenant_id: str, top_chunks: list[dict], top_k: int) -> list[dict]:
    from app.db.repositories import TenantRepository

    cap = min(12, max(top_k, DEFAULT_TOP_K) * 3)
    base = top_chunks[:top_k]
    neighbors = TenantRepository(db, tenant_id).fetch_neighbors(base, max(0, cap - len(base)))
    expanded: list[dict] = []
    seen: set[str] = set()

    for base_chunk in base:
        base_id = str(base_chunk["chunk_id"])
        prev = [n for n in neighbors if n.get("base_chunk_id") == base_id and n.get("ordinal") == base_chunk.get("ordinal", 0) - 1]
        nxt = [n for n in neighbors if n.get("base_chunk_id") == base_id and n.get("ordinal") == base_chunk.get("ordinal", 0) + 1]
        for c in [*prev, base_chunk, *nxt]:
            cid = str(c["chunk_id"])
            if cid in seen or len(expanded) >= cap:
                continue
            seen.add(cid)
            expanded.append(c)
    return expanded


def apply_context_budget(chunks: list[dict], max_context_words: int = MAX_CONTEXT_WORDS) -> tuple[list[dict], dict]:
    before = sum(token_count(c["chunk_text"]) for c in chunks)
    if before <= max_context_words:
        return chunks, {"context_word_count_before": before, "context_word_count_after": before, "chunks_dropped_count": 0}

    retained = list(chunks)
    dropped = 0
    while retained and sum(token_count(c["chunk_text"]) for c in retained) > max_context_words:
        idx = min(range(len(retained)), key=lambda i: (float(retained[i].get("final_score", 0.0)), retained[i].get("rank_position", 9999), retained[i]["chunk_id"]))
        retained.pop(idx)
        dropped += 1
    after = sum(token_count(c["chunk_text"]) for c in retained)
    return retained, {"context_word_count_before": before, "context_word_count_after": after, "chunks_dropped_count": dropped}
