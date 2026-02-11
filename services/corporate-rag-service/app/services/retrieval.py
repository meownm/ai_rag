import math
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


def min_max_normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        return [1.0 for _ in values]
    return [(v - min_v) / (max_v - min_v) for v in values]


def sigmoid_scale(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def hybrid_rank(
    query: str,
    candidates: list[dict],
    query_embedding: list[float],
    normalize_scores: bool = False,
) -> tuple[list[dict], dict[str, int]]:
    timer = {}
    t0 = time.perf_counter()
    for c in candidates:
        lex = c.get("lex_score", lexical_score(query, c["chunk_text"]))
        c["lex_score"] = float(lex)
        c["lex_raw"] = float(lex)
    timer["t_lexical_ms"] = int((time.perf_counter() - t0) * 1000)

    t1 = time.perf_counter()
    for c in candidates:
        computed = vector_score(query_embedding, c["embedding"])
        vec = max(float(c.get("vec_score", 0.0)), computed)
        c["vec_score"] = float(vec)
        c["vec_raw"] = float(vec)
    timer["t_vector_ms"] = int((time.perf_counter() - t1) * 1000)

    if normalize_scores:
        lex_norms = min_max_normalize([float(c.get("lex_raw", 0.0)) for c in candidates])
        vec_norms = min_max_normalize([float(c.get("vec_raw", 0.0)) for c in candidates])
        rerank_raws = [float(c.get("rerank_score", 0.0)) for c in candidates]
        rerank_norms = min_max_normalize(rerank_raws)
    else:
        lex_norms = [float(c.get("lex_score", 0.0)) for c in candidates]
        vec_norms = [float(c.get("vec_score", 0.0)) for c in candidates]
        rerank_norms = [float(c.get("rerank_score", 0.0)) for c in candidates]
        rerank_raws = [float(c.get("rerank_score", 0.0)) for c in candidates]

    for c, lex_norm, vec_norm, rerank_raw, rerank_norm in zip(candidates, lex_norms, vec_norms, rerank_raws, rerank_norms):
        boost = 0.05 if c.get("author") else 0.0
        c["boosts_applied"] = [{"name": "author_presence", "value": boost, "reason": "document has author"}] if boost else []

        c["lex_norm"] = float(lex_norm)
        c["vec_norm"] = float(vec_norm)
        c["rerank_raw"] = float(rerank_raw)
        c["rerank_norm"] = float(rerank_norm)

        if normalize_scores:
            c["final_score"] = (0.45 * c["lex_norm"]) + (0.45 * c["vec_norm"]) + (0.10 * c["rerank_norm"]) + boost
        else:
            c["final_score"] = (0.45 * c["lex_score"]) + (0.45 * c["vec_score"]) + (0.10 * c.get("rerank_score", 0.0)) + boost

    ranked = sorted(candidates, key=lambda x: x["final_score"], reverse=True)
    for idx, c in enumerate(ranked, start=1):
        c["rank_position"] = idx
    return ranked, timer
