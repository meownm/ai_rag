from typing import Any


def build_scoring_trace(trace_id: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for candidate in candidates:
        entries.append(
            {
                "chunk_id": str(candidate["chunk_id"]),
                "lex_score": float(candidate.get("lex_score", 0.0)),
                "vec_score": float(candidate.get("vec_score", 0.0)),
                "rerank_score": float(candidate.get("rerank_score", 0.0)),
                "lex_raw": float(candidate.get("lex_raw", candidate.get("lex_score", 0.0))),
                "lex_norm": float(candidate.get("lex_norm", candidate.get("lex_score", 0.0))),
                "vec_raw": float(candidate.get("vec_raw", candidate.get("vec_score", 0.0))),
                "vec_norm": float(candidate.get("vec_norm", candidate.get("vec_score", 0.0))),
                "rerank_raw": float(candidate.get("rerank_raw", candidate.get("rerank_score", 0.0))),
                "rerank_norm": float(candidate.get("rerank_norm", candidate.get("rerank_score", 0.0))),
                "boosts_applied": candidate.get("boosts_applied", []),
                "final_score": float(candidate.get("final_score", 0.0)),
                "rank_position": int(candidate.get("rank_position", 0)),
                "headings_path": candidate.get("heading_path", []),
                "title": candidate.get("title", ""),
                "labels": candidate.get("labels", []),
                "author": candidate.get("author"),
                "updated_at": candidate.get("updated_at", ""),
                "source_url": candidate.get("url", ""),
            }
        )

    return {
        "trace_id": trace_id,
        "scoring_trace": entries,
    }
