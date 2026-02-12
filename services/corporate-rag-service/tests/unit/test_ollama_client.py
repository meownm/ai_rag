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
    assert recorder.payload["options"]["num_ctx"] == client.num_ctx


def test_generate_accepts_custom_keep_alive(monkeypatch):
    recorder = DummyClient()

    def _fake_client(*_args, **_kwargs):
        return recorder

    monkeypatch.setattr("httpx.Client", _fake_client)

    client = OllamaClient(endpoint="http://ollama.local/api/generate", model="qwen", timeout_seconds=5)
    client.generate("hello", keep_alive=12)

    assert recorder.payload["keep_alive"] == 12


class DummyShowResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class DummyShowClient(DummyClient):
    def __init__(self, payload):
        super().__init__()
        self.payload = payload

    def post(self, _endpoint, json):
        self.payload_sent = json
        return DummyShowResponse(self.payload)


def test_fetch_model_num_ctx_from_show_details(monkeypatch):
    recorder = DummyShowClient({"details": {"num_ctx": 16384}})

    def _fake_client(*_args, **_kwargs):
        return recorder

    monkeypatch.setattr("httpx.Client", _fake_client)
    client = OllamaClient(endpoint="http://ollama.local/api/generate", model="qwen", timeout_seconds=5)

    assert client.fetch_model_num_ctx() == 16384


def test_fetch_model_num_ctx_from_model_info(monkeypatch):
    recorder = DummyShowClient({"model_info": {"llama.context_length": 32768}})

    def _fake_client(*_args, **_kwargs):
        return recorder

    monkeypatch.setattr("httpx.Client", _fake_client)
    client = OllamaClient(endpoint="http://ollama.local/api/generate", model="qwen", timeout_seconds=5)

    assert client.fetch_model_num_ctx() == 32768
