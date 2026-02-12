import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

import uuid

from app.api.routes import _fetch_candidates


def test_fetch_candidates_and_filtering_preserve_tenant_isolation(monkeypatch):
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())

    class FakeRepo:
        def __init__(self, _db, tenant_id):
            self.tenant_id = tenant_id

        def fetch_lexical_candidate_scores(self, _query, _top_n):
            return {"chunk-a": 0.9, "chunk-b": 0.9}

        def fetch_vector_candidates(self, _embedding, _top_n, use_similarity=False):
            return [{"chunk_id": "chunk-a", "vec_score": 0.9}, {"chunk_id": "chunk-b", "vec_score": 0.9}]

        def hydrate_candidates(self, _chunk_ids, lexical_scores, vector_score_map):
            return [
                {"chunk_id": "chunk-a", "tenant_id": self.tenant_id, "lex_score": lexical_scores["chunk-a"], "vec_score": vector_score_map["chunk-a"], "chunk_text": "a", "embedding": [1.0]},
                {"chunk_id": "chunk-b", "tenant_id": tenant_b, "lex_score": lexical_scores["chunk-b"], "vec_score": vector_score_map["chunk-b"], "chunk_text": "b", "embedding": [1.0]},
            ]

    monkeypatch.setattr("app.api.routes.TenantRepository", FakeRepo)

    candidates, *_ = _fetch_candidates(db=object(), tenant_id=tenant_a, query="policy", query_embedding=[1.0], top_n=5)
    tenant_safe = [c for c in candidates if c.get("tenant_id") == tenant_a]

    assert len(candidates) == 2
    assert [c["chunk_id"] for c in tenant_safe] == ["chunk-a"]
