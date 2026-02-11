from fastapi.testclient import TestClient

from app.main import app


class FakeSentenceTransformer:
    def __init__(self, values):
        self.values = values

    def encode(self, texts, normalize_embeddings=True):
        class V:
            def __init__(self, values):
                self.values = values

            def tolist(self):
                return self.values

        return [V(self.values) for _ in texts]


class FakeEncoderService:
    def __init__(self, model_id: str, values):
        self.model_id = model_id
        self._model = FakeSentenceTransformer(values)

    def encode(self, texts):
        return [v.tolist() for v in self._model.encode(texts)]


def test_embeddings_endpoint_positive(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "EMBEDDINGS_DEFAULT_MODEL_ID", "default-model")
    monkeypatch.setattr(
        routes.registry,
        "get_encoder",
        lambda model_id: FakeEncoderService(model_id=model_id, values=[0.1, 0.2]),
    )
    monkeypatch.setattr(routes.registry, "validate_embedding_dim", lambda model_id, vectors: len(vectors[0]))

    client = TestClient(app)
    response = client.post("/v1/embeddings", json={"input": ["hello"]})
    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "list"
    assert payload["model"] == "default-model"


def test_embeddings_endpoint_negative_validation(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "EMBEDDINGS_DEFAULT_MODEL_ID", "default-model")
    monkeypatch.setattr(
        routes.registry,
        "get_encoder",
        lambda model_id: FakeEncoderService(model_id=model_id, values=[0.1, 0.2]),
    )

    client = TestClient(app)
    response = client.post("/v1/embeddings", json={"input": []})
    assert response.status_code == 422


def test_embeddings_endpoint_dimension_mismatch_returns_error_code(monkeypatch):
    from app.api import routes
    from app.services.encoder import EmbeddingDimensionMismatchError

    monkeypatch.setattr(routes.settings, "EMBEDDINGS_DEFAULT_MODEL_ID", "default-model")
    monkeypatch.setattr(
        routes.registry,
        "get_encoder",
        lambda model_id: FakeEncoderService(model_id=model_id, values=[0.1, 0.2]),
    )

    def raise_dim_error(model_id, vectors):
        raise EmbeddingDimensionMismatchError(model_id=model_id, expected_dim=1024, actual_dim=2)

    monkeypatch.setattr(routes.registry, "validate_embedding_dim", raise_dim_error)

    client = TestClient(app)
    response = client.post("/v1/embeddings", json={"model": "custom-model", "input": ["hello"]})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error_code"] == "E-EMB-DIM-MISMATCH"


def test_healthz_returns_diagnostics(monkeypatch):
    from app.api import routes

    monkeypatch.setattr(routes.settings, "EMBEDDINGS_DEFAULT_MODEL_ID", "bge-m3")
    monkeypatch.setattr(routes.settings, "EMBEDDING_DIM", 1024)
    monkeypatch.setattr(routes.registry, "loaded_models", lambda: ["bge-m3", "custom-x"])

    client = TestClient(app)
    response = client.get("/v1/healthz")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["default_model_id"] == "bge-m3"
    assert payload["embedding_dim"] == 1024
    assert payload["loaded_models"] == ["bge-m3", "custom-x"]
