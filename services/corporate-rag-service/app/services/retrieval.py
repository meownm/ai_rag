import time
from collections import Counter


def _tokenize(text: str) -> list[str]:
    return [t for t in text.lower().split() if t.strip()]


def lexical_score(query: str, text: str) -> float:
    q = Counter(_tokenize(query))
    d = Counter(_tokenize(text))
    overlap = sum((q & d).values())
    return float(overlap / max(1, len(q)))


def vector_score(query_embedding: list[float], embedding: list[float]) -> float:
    dot = sum(a * b for a, b in zip(query_embedding, embedding))
    nq = sum(a * a for a in query_embedding) ** 0.5
    nd = sum(a * a for a in embedding) ** 0.5
    if nq == 0 or nd == 0:
        return 0.0
    return dot / (nq * nd)


def hybrid_rank(query: str, candidates: list[dict], query_embedding: list[float]) -> tuple[list[dict], dict[str, int]]:
    timer = {}
    t0 = time.perf_counter()
    for c in candidates:
        c["lex_score"] = lexical_score(query, c["chunk_text"])
    timer["t_lexical_ms"] = int((time.perf_counter() - t0) * 1000)

    t1 = time.perf_counter()
    for c in candidates:
        c["vec_score"] = vector_score(query_embedding, c["embedding"])
    timer["t_vector_ms"] = int((time.perf_counter() - t1) * 1000)

    for c in candidates:
        boost = 0.05 if c.get("author") else 0.0
        c["boosts_applied"] = [{"name": "author_presence", "value": boost, "reason": "document has author"}] if boost else []
        c["final_score"] = (0.45 * c["lex_score"]) + (0.45 * c["vec_score"]) + (0.10 * c.get("rerank_score", 0.0)) + boost

    ranked = sorted(candidates, key=lambda x: x["final_score"], reverse=True)
    for idx, c in enumerate(ranked, start=1):
        c["rank_position"] = idx
    return ranked, timer
