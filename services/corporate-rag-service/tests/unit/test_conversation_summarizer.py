import pytest

pytest.importorskip("pydantic")

from app.runners.conversation_summarizer import ConversationSummarizer


class FakeClient:
    def __init__(self, response: str):
        self.response = response

    def generate(self, *_args, **_kwargs):
        return {"response": self.response}


def test_summarizer_masked_mode_avoids_raw_quotes(monkeypatch):
    turns = [{"role": "user", "text": "My password is 12345"}, {"role": "assistant", "text": "Noted"}]
    summary = ConversationSummarizer().summarize(turns, masked_mode=True)

    assert "12345" not in summary
    assert "High-level summary (masked)" in summary


def test_summarizer_plain_mode_uses_llm_and_truncates(monkeypatch):
    long_response = "word " * 200
    monkeypatch.setattr("app.runners.conversation_summarizer.OllamaClient", lambda *_a, **_k: FakeClient(long_response))

    summary = ConversationSummarizer(model_id="qwen3:14b-instruct").summarize(
        [{"role": "user", "text": "summarize this"}],
        masked_mode=False,
    )

    assert len(summary.split()) <= 120
