import json

from app.services import anti_hallucination
from app.services.anti_hallucination import build_structured_refusal, verify_answer


def test_anti_hallucination_passes_supported_sentence(monkeypatch):
    monkeypatch.setattr(anti_hallucination, "_semantic_similarity", lambda *_args, **_kwargs: 1.0)
    valid, payload = verify_answer("Security training is required.", ["Security training is required for all employees."], 0.1, 0.2)
    assert valid is True
    assert payload["refusal_triggered"] is False


def test_anti_hallucination_rejects_unsupported_sentence(monkeypatch):
    monkeypatch.setattr(anti_hallucination, "_semantic_similarity", lambda *_args, **_kwargs: 0.0)
    valid, payload = verify_answer("Mars colony is approved.", ["Security training is required for all employees."], 0.9, 0.9)
    assert valid is False
    assert payload["refusal_triggered"] is True
    assert payload["unsupported_sentence_texts"]


def test_structured_refusal_payload_is_json():
    refusal = build_structured_refusal("trace-1", {"unsupported_sentences": 2})
    body = json.loads(refusal)
    assert body["refusal"]["code"] == "ONLY_SOURCES_VIOLATION"
    assert body["refusal"]["correlation_id"] == "trace-1"
