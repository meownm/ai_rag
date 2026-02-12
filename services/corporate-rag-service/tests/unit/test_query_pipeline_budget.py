import pytest

pytest.importorskip("pydantic")

from app.services.query_pipeline import TRUNCATION_MARKER, apply_context_budget, estimate_tokens


def test_estimate_tokens_fallback_positive(monkeypatch):
    monkeypatch.setattr("app.services.query_pipeline._tiktoken_estimate", lambda _text: (_ for _ in ()).throw(RuntimeError("no tiktoken")))
    est = estimate_tokens("one two three")
    assert est >= 3


def test_apply_context_budget_token_mode_enforces_budget_positive():
    chunks = [
        {"chunk_id": "1", "chunk_text": "a " * 200, "final_score": 1.0, "rank_position": 1},
        {"chunk_id": "2", "chunk_text": "b " * 200, "final_score": 0.9, "rank_position": 2},
        {"chunk_id": "3", "chunk_text": "c " * 200, "final_score": 0.8, "rank_position": 3},
    ]
    retained, log = apply_context_budget(chunks, use_token_budget_assembly=True, max_context_tokens=300)
    assert len(retained) >= 1
    assert log["total_context_tokens_est"] <= 300
    assert log["max_context_tokens"] == 300


def test_apply_context_budget_token_mode_truncates_top_chunk_negative():
    chunks = [
        {"chunk_id": "1", "chunk_text": "word " * 2000, "final_score": 1.0, "rank_position": 1},
        {"chunk_id": "2", "chunk_text": "other " * 200, "final_score": 0.9, "rank_position": 2},
    ]
    retained, log = apply_context_budget(chunks, use_token_budget_assembly=True, max_context_tokens=50)
    assert len(retained) == 1
    assert retained[0]["chunk_id"] == "1"
    assert TRUNCATION_MARKER in retained[0]["chunk_text"]
    assert log["truncated"] is True


def test_apply_context_budget_rejects_word_based_fallback_negative():
    with pytest.raises(ValueError, match="Word-based context trimming"):
        apply_context_budget([], use_token_budget_assembly=False)


def test_apply_context_budget_logs_initial_trimmed_final_tokens():
    chunks = [
        {"chunk_id": "1", "chunk_text": "a " * 400, "final_score": 1.0},
        {"chunk_id": "2", "chunk_text": "b " * 400, "final_score": 0.1},
    ]
    retained, log = apply_context_budget(chunks, use_token_budget_assembly=True, max_context_tokens=300)
    assert retained
    assert log["initial_tokens"] >= log["final_tokens"]
    assert log["trimmed_tokens"] == log["initial_tokens"] - log["final_tokens"]