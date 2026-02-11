from app.services.encoder import EmbeddingDimensionMismatchError, EncoderRegistry, EncoderService


class FakeSentenceTransformer:
    def encode(self, texts, normalize_embeddings=True):
        class V:
            def __init__(self, values):
                self.values = values

            def tolist(self):
                return self.values

        return [V([float(i + 1), 0.0]) for i, _ in enumerate(texts)]


def test_encode_batch():
    svc = EncoderService("fake", model=FakeSentenceTransformer())
    vectors = svc.encode(["a", "b"])
    assert len(vectors) == 2
    assert vectors[1][0] == 2.0


def test_registry_uses_model_id_as_cache_key(monkeypatch):
    created_models: list[str] = []

    def fake_init(self, model_id: str, model=None):
        self.model_id = model_id
        self.model = model
        created_models.append(model_id)

    monkeypatch.setattr("app.services.encoder.EncoderService.__init__", fake_init)
    registry = EncoderRegistry(expected_dim=2)

    first = registry.get_encoder("model-a")
    second = registry.get_encoder("model-b")
    first_again = registry.get_encoder("model-a")

    assert first is first_again
    assert first is not second
    assert created_models == ["model-a", "model-b"]


def test_dimension_mismatch_raises():
    registry = EncoderRegistry(expected_dim=3)

    try:
        registry.validate_embedding_dim("model-a", [[1.0, 2.0]])
    except EmbeddingDimensionMismatchError as exc:
        assert exc.model_id == "model-a"
        assert exc.expected_dim == 3
        assert exc.actual_dim == 2
    else:
        raise AssertionError("Expected EmbeddingDimensionMismatchError")
