import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

from app.api.routes import _assert_prompt_within_num_ctx, _ground_citations, _should_reset_topic, _trim_history_turns


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


def test_ground_citations_strips_hallucinated_chunk_id():
    allowed = {("c1", "d1"), ("c2", "d2")}
    citations = [{"chunk_id": "c1", "document_id": "d1"}, {"chunk_id": "missing", "document_id": "d9"}]
    grounded, stripped = _ground_citations(citations, allowed)
    assert stripped is True
    assert grounded == [{"chunk_id": "c1", "document_id": "d1"}]


def test_ground_citations_accepts_retrieved_chunk_ids_only():
    allowed = {("c1", "d1"), ("c2", "d2")}
    citations = [{"chunk_id": "c1", "document_id": "d1"}, {"chunk_id": "c2", "document_id": "d2"}]
    grounded, stripped = _ground_citations(citations, allowed)
    assert stripped is False
    assert grounded == citations


def test_ground_citations_rejects_non_list_negative():
    grounded, stripped = _ground_citations({"chunk_id": "c1"}, {("c1", "d1")})
    assert stripped is True
    assert grounded == []

def test_should_reset_topic_positive():
    reset, similarity = _should_reset_topic([1.0, 0.0], [0.0, 1.0], 0.35)
    assert reset is True
    assert similarity == pytest.approx(0.0)


def test_should_reset_topic_negative():
    reset, similarity = _should_reset_topic([1.0, 0.0], [0.9, 0.1], 0.35)
    assert reset is False
    assert similarity > 0.35

def test_ground_citations_rejects_missing_document_id_negative():
    allowed = {("c1", "d1")}
    citations = [{"chunk_id": "c1"}]
    grounded, stripped = _ground_citations(citations, allowed)
    assert stripped is True
    assert grounded == []


def test_assert_prompt_within_num_ctx_raises_on_overflow(monkeypatch):
    monkeypatch.setattr("app.api.routes.settings.LLM_NUM_CTX", 100)
    monkeypatch.setattr("app.api.routes.settings.TOKEN_BUDGET_SAFETY_MARGIN", 10)

    with pytest.raises(ValueError, match="TOKEN_BUDGET_EXCEEDED"):
        _assert_prompt_within_num_ctx("word " * 200)


def test_assert_prompt_within_num_ctx_accepts_prompt_within_limit(monkeypatch):
    monkeypatch.setattr("app.api.routes.settings.LLM_NUM_CTX", 1000)
    monkeypatch.setattr("app.api.routes.settings.TOKEN_BUDGET_SAFETY_MARGIN", 50)

    _assert_prompt_within_num_ctx("concise prompt")
