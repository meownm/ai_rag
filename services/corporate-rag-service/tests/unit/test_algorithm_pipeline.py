import pytest

pytest.importorskip("sqlalchemy")

import uuid

from app.services.query_pipeline import apply_context_budget, expand_neighbors
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


def test_vector_retrieval_uses_pgvector_sql_and_tenant_filter():
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
    rows = repo.fetch_vector_candidates([1.0, 0.0], 2)
    assert rows[0]["chunk_id"] == "a"
    assert rows[0]["vec_score"] > rows[1]["vec_score"]
    assert "<=>" in captured["sql"]
    assert "cv.tenant_id = CAST(:tenant_id AS uuid)" in captured["sql"]


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
    expanded = expand_neighbors(object(), "t", base, 1)
    assert [c["chunk_id"] for c in expanded] == ["a", "b", "c"]
    assert len(expanded) <= 12


def test_context_budget_drops_lowest_scores_deterministically():
    chunks = [
        {"chunk_id": "1", "chunk_text": "a " * 8000, "final_score": 0.9, "rank_position": 1},
        {"chunk_id": "2", "chunk_text": "b " * 5000, "final_score": 0.2, "rank_position": 2},
        {"chunk_id": "3", "chunk_text": "c " * 5000, "final_score": 0.8, "rank_position": 3},
    ]
    retained, log = apply_context_budget(chunks, max_context_words=12000)
    assert [c["chunk_id"] for c in retained] == ["1", "3"]
    assert log["chunks_dropped_count"] == 1
