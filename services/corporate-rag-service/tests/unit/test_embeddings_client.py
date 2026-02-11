import pytest

from app.clients.embeddings_client import EmbeddingsClient


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeHttpxClient:
    def __init__(self, recorder):
        self.recorder = recorder

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, json):
        self.recorder.append((url, json))
        return FakeResponse({"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]})


def test_embed_texts_positive_batches_payload(monkeypatch):
    calls = []

    monkeypatch.setattr("httpx.Client", lambda timeout: FakeHttpxClient(calls))
    client = EmbeddingsClient(base_url="http://emb", timeout_seconds=5)
    vectors = client.embed_texts(["a", "b"], model_id="m1", tenant_id="t1", correlation_id="c1")

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert calls[0][0] == "http://emb/v1/embeddings"
    assert calls[0][1]["model"] == "m1"
    assert calls[0][1]["input"] == ["a", "b"]


def test_embed_text_negative_empty_data(monkeypatch):
    class EmptyDataHttpxClient(FakeHttpxClient):
        def post(self, url, json):
            return FakeResponse({"data": []})

    monkeypatch.setattr("httpx.Client", lambda timeout: EmptyDataHttpxClient([]))
    client = EmbeddingsClient(base_url="http://emb", timeout_seconds=5)

    with pytest.raises(RuntimeError):
        client.embed_text("x")
