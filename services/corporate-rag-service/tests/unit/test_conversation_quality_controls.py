import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

from app.api.routes import _has_invalid_citations, _should_reset_topic, _trim_history_turns


def test_trim_history_turns_enforces_turn_and_token_limits(monkeypatch):
    monkeypatch.setattr("app.api.routes.settings.MAX_HISTORY_TURNS", 3)
    monkeypatch.setattr("app.api.routes.settings.MAX_HISTORY_TOKENS", 8)

    turns = [
        {"role": "user", "text": "one two three"},
        {"role": "assistant", "text": "a b c"},
        {"role": "user", "text": "d e f"},
        {"role": "assistant", "text": "g h i"},
    ]

    trimmed = _trim_history_turns(turns)
    assert len(trimmed) <= 3
    assert trimmed[-1]["text"] == "g h i"


def test_has_invalid_citations_rejects_hallucinated_chunk_id():
    allowed = {("c1", "d1"), ("c2", "d2")}
    citations = [{"chunk_id": "c1", "document_id": "d1"}, {"chunk_id": "missing", "document_id": "d9"}]
    assert _has_invalid_citations(citations, allowed) is True


def test_has_invalid_citations_accepts_retrieved_chunk_ids_only():
    allowed = {("c1", "d1"), ("c2", "d2")}
    citations = [{"chunk_id": "c1", "document_id": "d1"}, {"chunk_id": "c2", "document_id": "d2"}]
    assert _has_invalid_citations(citations, allowed) is False


def test_has_invalid_citations_rejects_non_list_negative():
    assert _has_invalid_citations({"chunk_id": "c1"}, {("c1", "d1")}) is True

def test_should_reset_topic_positive():
    reset, similarity = _should_reset_topic([1.0, 0.0], [0.0, 1.0], 0.35)
    assert reset is True
    assert similarity == pytest.approx(0.0)


def test_should_reset_topic_negative():
    reset, similarity = _should_reset_topic([1.0, 0.0], [0.9, 0.1], 0.35)
    assert reset is False
    assert similarity > 0.35

def test_has_invalid_citations_rejects_missing_document_id_negative():
    allowed = {("c1", "d1")}
    citations = [{"chunk_id": "c1"}]
    assert _has_invalid_citations(citations, allowed) is True
