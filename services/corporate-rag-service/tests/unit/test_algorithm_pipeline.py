import pytest

pytest.importorskip("sqlalchemy")

import uuid

from app.services.query_pipeline import apply_context_budget, expand_neighbors
from app.services.retrieval import hybrid_rank, min_max_normalize
from app.cli.fts_rebuild import weighted_fts_expression
from app.db.repositories import TenantRepository


class FakeMappings:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeExecResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return FakeMappings(self.rows)


class FakeNeighborRepo:
    def __init__(self, neighbors):
        self.neighbors = neighbors

    def fetch_neighbors(self, _base, _cap):
        return self.neighbors


def test_vector_retrieval_uses_pgvector_similarity_sql_and_tenant_filter():
    captured = {}

    class FakeDB:
        def execute(self, statement, params):
            captured["sql"] = str(statement)
            captured["params"] = params
            return FakeExecResult([
                {"chunk_id": "a", "distance": 0.1, "vec_score": 0.91},
                {"chunk_id": "b", "distance": 0.9, "vec_score": 0.52},
            ])

    repo = TenantRepository(FakeDB(), "11111111-1111-1111-1111-111111111111")
    rows = repo.fetch_vector_candidates_by_similarity([1.0, 0.0], 2)
    assert rows[0]["chunk_id"] == "a"
    assert rows[0]["vec_score"] > rows[1]["vec_score"]
    assert "<->" in captured["sql"]
    assert "cv.tenant_id = CAST(:tenant_id AS uuid)" in captured["sql"]


def test_vector_retrieval_flag_off_preserves_ordinal_behavior():
    captured = {}

    class FakeDB:
        def execute(self, statement, params):
            captured["sql"] = str(statement)
            captured["params"] = params
            return FakeExecResult([
                {"chunk_id": "old-1", "distance": 0.0, "vec_score": 0.0},
                {"chunk_id": "old-2", "distance": 0.0, "vec_score": 0.0},
            ])

    repo = TenantRepository(FakeDB(), "11111111-1111-1111-1111-111111111111")
    rows = repo.fetch_vector_candidates([1.0, 0.0], 2, use_similarity=False)

    assert [r["chunk_id"] for r in rows] == ["old-1", "old-2"]
    assert "ORDER BY c.ordinal ASC" in captured["sql"]
    assert "<->" not in captured["sql"]


def test_vector_retrieval_flag_on_uses_similarity_behavior():
    captured = {}

    class FakeDB:
        def execute(self, statement, params):
            captured["sql"] = str(statement)
            captured["params"] = params
            return FakeExecResult([
                {"chunk_id": "sim-1", "distance": 0.1, "vec_score": 0.9},
            ])

    repo = TenantRepository(FakeDB(), "11111111-1111-1111-1111-111111111111")
    rows = repo.fetch_vector_candidates([1.0, 0.0], 1, use_similarity=True)

    assert rows[0]["chunk_id"] == "sim-1"
    assert "ORDER BY cv.embedding <-> CAST(:qvec AS vector)" in captured["sql"]


def test_weighted_fts_expression_includes_title_labels_and_text():
    expr = weighted_fts_expression()
    assert "d.title" in expr
    assert "d.labels" in expr
    assert "c.chunk_text" in expr


def test_neighbor_expansion_keeps_same_tenant_and_cap(monkeypatch):
    base = [{"chunk_id": "b", "document_id": uuid.uuid4(), "ordinal": 2, "tenant_id": "t", "chunk_text": "base", "final_score": 1.0, "vec_score": 0.7, "rerank_score": 0.6, "boosts_applied": []}]
    neighbors = [
        {"chunk_id": "a", "document_id": base[0]["document_id"], "ordinal": 1, "tenant_id": "t", "chunk_text": "prev", "final_score": 0.9, "vec_score": 0.6, "rerank_score": 0.5, "base_chunk_id": "b"},
        {"chunk_id": "c", "document_id": base[0]["document_id"], "ordinal": 3, "tenant_id": "t", "chunk_text": "next", "final_score": 0.9, "vec_score": 0.6, "rerank_score": 0.5, "base_chunk_id": "b"},
    ]

    monkeypatch.setattr("app.db.repositories.TenantRepository", lambda *_args, **_kwargs: FakeNeighborRepo(neighbors))
    expanded = expand_neighbors(object(), "t", base, 1, use_contextual_expansion=True, neighbor_window=1)
    assert [c["chunk_id"] for c in expanded] == ["a", "b", "c"]
    assert len(expanded) <= 12


def test_neighbor_expansion_flag_off_returns_base_only(monkeypatch):
    base = [{"chunk_id": "b", "document_id": uuid.uuid4(), "ordinal": 2, "tenant_id": "t", "chunk_text": "base"}]
    neighbors = [{"chunk_id": "a", "document_id": base[0]["document_id"], "ordinal": 1, "tenant_id": "t", "chunk_text": "prev"}]
    monkeypatch.setattr("app.db.repositories.TenantRepository", lambda *_args, **_kwargs: FakeNeighborRepo(neighbors))

    expanded = expand_neighbors(object(), "t", base, 1, use_contextual_expansion=False, neighbor_window=1)
    assert [c["chunk_id"] for c in expanded] == ["b"]


def test_neighbor_expansion_deduplicates_and_preserves_order(monkeypatch):
    doc = uuid.uuid4()
    base = [{"chunk_id": "b", "document_id": doc, "ordinal": 2, "tenant_id": "t", "chunk_text": "base"}]
    neighbors = [
        {"chunk_id": "c", "document_id": doc, "ordinal": 3, "tenant_id": "t", "chunk_text": "next"},
        {"chunk_id": "a", "document_id": doc, "ordinal": 1, "tenant_id": "t", "chunk_text": "prev"},
        {"chunk_id": "b", "document_id": doc, "ordinal": 2, "tenant_id": "t", "chunk_text": "dup-base"},
    ]
    monkeypatch.setattr("app.db.repositories.TenantRepository", lambda *_args, **_kwargs: FakeNeighborRepo(neighbors))

    expanded = expand_neighbors(object(), "t", base, 1, use_contextual_expansion=True, neighbor_window=1)
    assert [c["chunk_id"] for c in expanded] == ["a", "b", "c"]


def test_context_budget_drops_lowest_scores_deterministically():
    chunks = [
        {"chunk_id": "1", "chunk_text": "a " * 8000, "final_score": 0.9, "rank_position": 1},
        {"chunk_id": "2", "chunk_text": "b " * 5000, "final_score": 0.2, "rank_position": 2},
        {"chunk_id": "3", "chunk_text": "c " * 5000, "final_score": 0.8, "rank_position": 3},
    ]
    retained, log = apply_context_budget(chunks, max_context_words=12000)
    assert [c["chunk_id"] for c in retained] == ["1", "3"]
    assert log["chunks_dropped_count"] == 1


def test_min_max_normalize_edge_cases():
    assert min_max_normalize([]) == []
    assert min_max_normalize([2.0, 2.0, 2.0]) == [1.0, 1.0, 1.0]
    scaled = min_max_normalize([1.0, 2.0, 3.0])
    assert scaled == [0.0, 0.5, 1.0]


def test_hybrid_rank_with_normalization_adds_raw_and_norm_fields():
    candidates = [
        {
            "chunk_id": "a",
            "chunk_text": "alpha policy",
            "embedding": [1.0, 0.0],
            "lex_score": 10.0,
            "vec_score": 0.1,
            "rerank_score": 3.0,
            "author": "x",
        },
        {
            "chunk_id": "b",
            "chunk_text": "beta policy",
            "embedding": [0.0, 1.0],
            "lex_score": 20.0,
            "vec_score": 0.9,
            "rerank_score": 1.0,
            "author": None,
        },
    ]

    ranked, _ = hybrid_rank("policy", candidates, [1.0, 0.0], normalize_scores=True)
    for entry in ranked:
        assert "lex_raw" in entry
        assert "lex_norm" in entry
        assert "vec_raw" in entry
        assert "vec_norm" in entry
        assert "rerank_raw" in entry
        assert "rerank_norm" in entry
        assert 0.0 <= entry["lex_norm"] <= 1.0
        assert 0.0 <= entry["vec_norm"] <= 1.0
        assert 0.0 <= entry["rerank_norm"] <= 1.0


def test_hybrid_rank_deduplicates_before_sort_and_uses_chunk_id_tiebreak(monkeypatch):
    monkeypatch.setattr("app.services.retrieval.settings.HYBRID_WEIGHT_VECTOR", 0.7)
    monkeypatch.setattr("app.services.retrieval.settings.HYBRID_WEIGHT_FTS", 0.3)
    candidates = [
        {"chunk_id": "b", "chunk_text": "policy", "embedding": [1.0, 0.0], "lex_score": 1.0, "vec_score": 0.5, "rerank_score": 0.0},
        {"chunk_id": "a", "chunk_text": "policy", "embedding": [1.0, 0.0], "lex_score": 1.0, "vec_score": 0.5, "rerank_score": 0.0},
        {"chunk_id": "a", "chunk_text": "policy", "embedding": [1.0, 0.0], "lex_score": 0.2, "vec_score": 0.4, "rerank_score": 0.0},
    ]

    ranked, _ = hybrid_rank("policy", candidates, [1.0, 0.0], normalize_scores=True)
    assert [row["chunk_id"] for row in ranked] == ["a", "b"]


def test_hybrid_rank_applies_configured_weighted_merge(monkeypatch):
    monkeypatch.setattr("app.services.retrieval.settings.HYBRID_WEIGHT_VECTOR", 0.9)
    monkeypatch.setattr("app.services.retrieval.settings.HYBRID_WEIGHT_FTS", 0.1)
    candidates = [
        {"chunk_id": "a", "chunk_text": "policy", "embedding": [1.0, 0.0], "lex_score": 10.0, "vec_score": 0.1, "rerank_score": 0.0},
        {"chunk_id": "b", "chunk_text": "policy", "embedding": [0.0, 1.0], "lex_score": 0.1, "vec_score": 0.9, "rerank_score": 0.0},
    ]

    ranked, _ = hybrid_rank("policy", candidates, [1.0, 0.0], normalize_scores=True)
    assert ranked[0]["chunk_id"] == "b"
    assert 0.0 <= ranked[0]["hybrid_score"] <= 1.0


def test_hybrid_rank_final_score_matches_weighted_formula(monkeypatch):
    monkeypatch.setattr("app.services.retrieval.settings.HYBRID_WEIGHT_VECTOR", 0.7)
    monkeypatch.setattr("app.services.retrieval.settings.HYBRID_WEIGHT_FTS", 0.3)
    candidates = [
        {"chunk_id": "a", "chunk_text": "policy", "embedding": [1.0, 0.0], "lex_score": 0.2, "vec_score": 0.8, "rerank_score": 0.6},
        {"chunk_id": "b", "chunk_text": "policy", "embedding": [0.0, 1.0], "lex_score": 0.6, "vec_score": 0.2, "rerank_score": 0.1},
    ]

    ranked, _ = hybrid_rank("policy", candidates, [1.0, 0.0], normalize_scores=True)
    for row in ranked:
        expected = (0.7 * row["vec_norm"]) + (0.3 * row["lex_norm"])
        assert row["final_score"] == pytest.approx(expected)
