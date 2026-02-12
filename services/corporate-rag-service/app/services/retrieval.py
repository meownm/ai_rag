import math
import time
from collections import Counter

from app.core.config import settings


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


def _normalize_similarity_01(value: float) -> float:
    clipped = max(-1.0, min(1.0, float(value)))
    return (clipped + 1.0) / 2.0


def _dedup_by_chunk_id(candidates: list[dict]) -> list[dict]:
    by_chunk: dict[str, dict] = {}
    for candidate in candidates:
        chunk_id = str(candidate.get("chunk_id"))
        existing = by_chunk.get(chunk_id)
        if existing is None:
            by_chunk[chunk_id] = candidate
            continue

        if float(candidate.get("vec_score", 0.0)) > float(existing.get("vec_score", 0.0)):
            existing["vec_score"] = float(candidate.get("vec_score", 0.0))
        if float(candidate.get("lex_score", 0.0)) > float(existing.get("lex_score", 0.0)):
            existing["lex_score"] = float(candidate.get("lex_score", 0.0))
        if float(candidate.get("rerank_score", 0.0)) > float(existing.get("rerank_score", 0.0)):
            existing["rerank_score"] = float(candidate.get("rerank_score", 0.0))
    return list(by_chunk.values())


def hybrid_rank(
    query: str,
    candidates: list[dict],
    query_embedding: list[float],
    normalize_scores: bool = False,
) -> tuple[list[dict], dict[str, int]]:
    timer = {}
    t0 = time.perf_counter()
    candidates = _dedup_by_chunk_id(candidates)

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

    # R6: keep both channels normalized into [0,1] for deterministic weighted merge.
    fts_raws = [max(0.0, float(c.get("lex_raw", 0.0))) for c in candidates]
    vec_raws = [_normalize_similarity_01(float(c.get("vec_raw", 0.0))) for c in candidates]
    lex_norms = min_max_normalize(fts_raws)
    vec_norms = min_max_normalize(vec_raws)
    rerank_raws = [float(c.get("rerank_score", 0.0)) for c in candidates]
    rerank_norms = min_max_normalize(rerank_raws) if normalize_scores else rerank_raws

    weight_vec = float(settings.HYBRID_W_VECTOR)
    weight_fts = float(settings.HYBRID_W_FTS)

    for c, lex_norm, vec_norm, rerank_raw, rerank_norm in zip(candidates, lex_norms, vec_norms, rerank_raws, rerank_norms):
        boost = 0.05 if c.get("author") else 0.0
        c["boosts_applied"] = [{"name": "author_presence", "value": boost, "reason": "document has author"}] if boost else []

        c["lex_norm"] = float(max(0.0, min(1.0, lex_norm)))
        c["vec_norm"] = float(max(0.0, min(1.0, vec_norm)))
        c["rerank_raw"] = float(rerank_raw)
        c["rerank_norm"] = float(rerank_norm)

        c["hybrid_score"] = (weight_vec * c["vec_norm"]) + (weight_fts * c["lex_norm"])
        c["final_score"] = c["hybrid_score"]

    ranked = sorted(
        candidates,
        key=lambda x: (
            -float(x.get("final_score", 0.0)),
            -int(x.get("source_preference", 0)),
            str(x.get("chunk_id")),
        ),
    )
    for idx, c in enumerate(ranked, start=1):
        c["rank_position"] = idx
    return ranked, timer
