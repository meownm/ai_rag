from fastapi.testclient import TestClient

from app.main import app
from app.services.encoder import EncoderService


class FakeSentenceTransformer:
    def encode(self, texts, normalize_embeddings=True):
        class V:
            def __init__(self, values):
                self.values = values

            def tolist(self):
                return self.values

        return [V([0.1, 0.2]) for _ in texts]


def test_embeddings_endpoint_positive(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes, "get_encoder", lambda: EncoderService("fake", model=FakeSentenceTransformer()))
    client = TestClient(app)
    response = client.post("/v1/embeddings", json={"model": "fake", "input": ["hello"]})
    assert response.status_code == 200
    assert response.json()["object"] == "list"


def test_embeddings_endpoint_negative_validation(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes, "get_encoder", lambda: EncoderService("fake", model=FakeSentenceTransformer()))
    client = TestClient(app)
    response = client.post("/v1/embeddings", json={"model": "fake", "input": []})
    assert response.status_code == 422
