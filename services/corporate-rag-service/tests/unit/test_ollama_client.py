from app.clients.ollama_client import OllamaClient


class DummyResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"response": "ok"}


class DummyClient:
    def __init__(self):
        self.payload = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def post(self, _endpoint, json):
        self.payload = json
        return DummyResponse()


def test_generate_includes_keep_alive_zero(monkeypatch):
    recorder = DummyClient()

    def _fake_client(*_args, **_kwargs):
        return recorder

    monkeypatch.setattr("httpx.Client", _fake_client)

    client = OllamaClient(endpoint="http://ollama.local/api/generate", model="qwen", timeout_seconds=5)
    response = client.generate("hello", keep_alive=0)

    assert response == {"response": "ok"}
    assert recorder.payload["keep_alive"] == 0


def test_generate_accepts_custom_keep_alive(monkeypatch):
    recorder = DummyClient()

    def _fake_client(*_args, **_kwargs):
        return recorder

    monkeypatch.setattr("httpx.Client", _fake_client)

    client = OllamaClient(endpoint="http://ollama.local/api/generate", model="qwen", timeout_seconds=5)
    client.generate("hello", keep_alive=12)

    assert recorder.payload["keep_alive"] == 12
