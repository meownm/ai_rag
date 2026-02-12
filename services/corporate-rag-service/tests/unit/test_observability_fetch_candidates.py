import pytest

pytest.importorskip("sqlalchemy")

from app.api import routes


class FakeRepo:
    def __init__(self, *_args, **_kwargs):
        pass

    def fetch_lexical_candidate_scores(self, _query, _k_lex):
        return {"chunk-a": 0.5, "chunk-b": 0.1}

    def fetch_vector_candidates(self, _query_embedding, _k_vec, use_similarity=False):
        assert isinstance(use_similarity, bool)
        return [{"chunk_id": "chunk-a", "vec_score": 0.9}, {"chunk_id": "chunk-c", "vec_score": 0.3}]

    def hydrate_candidates(self, chunk_ids, lexical_scores, vector_scores):
        assert chunk_ids == {"chunk-a", "chunk-b", "chunk-c"}
        assert "chunk-a" in lexical_scores
        assert "chunk-c" in vector_scores
        return [{"chunk_id": "chunk-a"}, {"chunk_id": "chunk-b"}, {"chunk_id": "chunk-c"}]


def test_fetch_candidates_returns_counts(monkeypatch):
    monkeypatch.setattr(routes, "TenantRepository", FakeRepo)

    candidates, lexical_ms, fts_count, vector_count = routes._fetch_candidates(
        db=object(),
        tenant_id="tenant-1",
        query="hello",
        query_embedding=[0.1, 0.2],
        top_n=5,
    )

    assert len(candidates) == 3
    assert lexical_ms >= 0
    assert fts_count == 2
    assert vector_count == 2
