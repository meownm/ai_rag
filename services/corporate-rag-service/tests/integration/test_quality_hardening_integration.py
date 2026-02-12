import pytest

pytest.importorskip("pydantic")
pytest.importorskip("fastapi")

from app.api.routes import _has_invalid_citations, _should_reset_topic
from app.services.query_pipeline import apply_context_budget
from app.services.retrieval import hybrid_rank


def test_hybrid_then_budget_flow_is_deterministic_integration(monkeypatch):
    monkeypatch.setattr("app.services.retrieval.settings.HYBRID_WEIGHT_VECTOR", 0.7)
    monkeypatch.setattr("app.services.retrieval.settings.HYBRID_WEIGHT_FTS", 0.3)

    candidates = [
        {"chunk_id": "c3", "chunk_text": "policy three", "embedding": [0.4, 0.6], "lex_score": 0.4, "vec_score": 0.4, "rerank_score": 0.0, "final_score": 0.0},
        {"chunk_id": "c1", "chunk_text": "policy one " * 300, "embedding": [1.0, 0.0], "lex_score": 0.8, "vec_score": 0.8, "rerank_score": 0.0, "final_score": 0.0},
        {"chunk_id": "c2", "chunk_text": "policy two " * 280, "embedding": [0.9, 0.1], "lex_score": 0.7, "vec_score": 0.7, "rerank_score": 0.0, "final_score": 0.0},
    ]

    ranked_first, _ = hybrid_rank("policy", [dict(c) for c in candidates], [1.0, 0.0], normalize_scores=True)
    ranked_second, _ = hybrid_rank("policy", [dict(c) for c in candidates], [1.0, 0.0], normalize_scores=True)
    assert [c["chunk_id"] for c in ranked_first] == [c["chunk_id"] for c in ranked_second]

    retained, log = apply_context_budget(ranked_first, use_token_budget_assembly=True, max_context_tokens=420)
    assert [c["chunk_id"] for c in retained] == [c["chunk_id"] for c in apply_context_budget(ranked_second, use_token_budget_assembly=True, max_context_tokens=420)[0]]
    assert log["final_tokens"] <= 420


def test_topic_reset_and_citation_safety_integration():
    reset, similarity = _should_reset_topic([1.0, 0.0], [0.0, 1.0], threshold=0.35)
    assert reset is True
    assert similarity == pytest.approx(0.0)

    assert _has_invalid_citations([{"chunk_id": "retrieved-1"}], {"retrieved-1", "retrieved-2"}) is False
    assert _has_invalid_citations([{"chunk_id": "hallucinated"}], {"retrieved-1", "retrieved-2"}) is True
