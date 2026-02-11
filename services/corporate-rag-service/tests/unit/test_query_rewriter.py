import json

import pytest

pytest.importorskip("pydantic")

from app.runners.query_rewriter import QueryRewriteError, QueryRewriter


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.keep_alive = None
        self.prompt = None

    def generate(self, prompt, *, keep_alive=0):
        self.keep_alive = keep_alive
        self.prompt = prompt
        return self.payload


def test_rewriter_accepts_valid_schema(monkeypatch):
    payload = {
        "response": json.dumps(
            {
                "resolved_query_text": "corporate vacation policy",
                "follow_up": True,
                "topic_shift": False,
                "intent": "policy_lookup",
                "entities": [{"type": "policy", "value": "vacation"}],
                "clarification_needed": False,
                "clarification_question": None,
                "confidence": 0.92,
            }
        )
    }
    fake = FakeClient(payload)
    monkeypatch.setattr("app.runners.query_rewriter.OllamaClient", lambda *_a, **_k: fake)

    result = QueryRewriter(model_id="qwen3:14b-instruct", keep_alive=0).rewrite(
        tenant_id="11111111-1111-1111-1111-111111111111",
        conversation_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        user_query="what about vacation?",
        recent_turns=[{"role": "user", "text": "tell me about leave"}],
        summary="HR topics",
        citation_hints=[{"source": "kb", "title": "HR", "chunk_ordinal": 1}],
    )

    assert result.resolved_query_text == "corporate vacation policy"
    assert result.confidence == 0.92
    assert fake.keep_alive == 0


def test_rewriter_rejects_invalid_schema(monkeypatch):
    payload = {
        "response": json.dumps(
            {
                "resolved_query_text": "",
                "follow_up": True,
                "topic_shift": False,
                "intent": "policy_lookup",
                "entities": [{"type": "policy", "value": "vacation"}],
                "clarification_needed": False,
                "clarification_question": None,
                "confidence": 2.0,
            }
        )
    }
    monkeypatch.setattr("app.runners.query_rewriter.OllamaClient", lambda *_a, **_k: FakeClient(payload))

    with pytest.raises(QueryRewriteError):
        QueryRewriter(model_id="qwen3:14b-instruct", keep_alive=0).rewrite(
            tenant_id="11111111-1111-1111-1111-111111111111",
            conversation_id=None,
            user_query="vacation",
            recent_turns=[],
        )


def test_rewriter_includes_pending_clarification_in_prompt(monkeypatch):
    payload = {
        "response": json.dumps(
            {
                "resolved_query_text": "resolved",
                "follow_up": True,
                "topic_shift": False,
                "intent": "policy_lookup",
                "entities": [{"type": "policy", "value": "vacation"}],
                "clarification_needed": False,
                "clarification_question": None,
                "confidence": 0.9,
            }
        )
    }
    fake = FakeClient(payload)
    monkeypatch.setattr("app.runners.query_rewriter.OllamaClient", lambda *_a, **_k: fake)

    QueryRewriter(model_id="qwen3:14b-instruct", keep_alive=0).rewrite(
        tenant_id="11111111-1111-1111-1111-111111111111",
        conversation_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        user_query="it",
        recent_turns=[{"role": "assistant", "text": "Which policy?"}],
        clarification_pending=True,
        last_question="Which policy?",
    )

    assert "ClarificationPending: true" in fake.prompt
    assert "Which policy?" in fake.prompt
