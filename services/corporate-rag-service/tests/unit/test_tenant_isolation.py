from pathlib import Path
import logging
import uuid

from app.services.retrieval import hybrid_rank


class _FakeReranker:
    def rerank(self, query: str, candidates: list[dict]) -> tuple[list[dict], int]:
        logging.getLogger("app.services.reranker").info("reranker_applied", extra={"candidate_count": len(candidates)})
        for c in candidates:
            c["rerank_score"] = c.get("rerank_score", 0.9)
        return candidates, 1


def test_tenant_filter_blocks_cross_tenant_results_and_reranker_logs(caplog):
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    query_embedding = [1.0, 0.0]
    caplog.set_level(logging.INFO)

    candidates = [
        {
            "chunk_id": "chunk-a",
            "document_id": "doc-a",
            "chunk_text": "Tenant A only content",
            "embedding": [1.0, 0.0],
            "tenant_id": tenant_a,
            "boosts_applied": [],
            "rerank_score": 0.1,
            "lex_score": 0.7,
        },
        {
            "chunk_id": "chunk-b",
            "document_id": "doc-b",
            "chunk_text": "Tenant B secret content",
            "embedding": [1.0, 0.0],
            "tenant_id": tenant_b,
            "boosts_applied": [],
            "rerank_score": 0.1,
            "lex_score": 0.7,
        },
    ]

    ranked, _ = hybrid_rank("tenant content", candidates, query_embedding)
    reranked, _ = _FakeReranker().rerank("tenant content", ranked)
    ranked_final, _ = hybrid_rank("tenant content", reranked, query_embedding)

    tenant_safe_ranked = [c for c in ranked_final if c.get("tenant_id") == tenant_a]
    cited_chunk_ids = {c["chunk_id"] for c in tenant_safe_ranked}
    cited_document_ids = {c["document_id"] for c in tenant_safe_ranked}

    assert "chunk-b" not in cited_chunk_ids
    assert "doc-b" not in cited_document_ids
    assert any("reranker_applied" in rec.message for rec in caplog.records)


def test_tenant_guard_static_scan_for_critical_queries():
    files = [
        "app/api/routes.py",
        "app/services/audit.py",
        "app/services/ingestion.py",
    ]
    forbidden = ["db.query(Chunks)", "db.query(Documents)", "db.query(ChunkVectors)", "db.query(EventLogs)"]

    root = Path(__file__).resolve().parents[2]
    for rel_path in files:
        content = (root / rel_path).read_text(encoding="utf-8")
        for pattern in forbidden:
            assert pattern not in content, f"forbidden pattern {pattern} in {rel_path}"
