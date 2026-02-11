class EmbeddingDimensionMismatchError(Exception):
    def __init__(self, model_id: str, expected_dim: int, actual_dim: int):
        super().__init__(f"Model {model_id} produced dim={actual_dim}, expected={expected_dim}")
        self.model_id = model_id
        self.expected_dim = expected_dim
        self.actual_dim = actual_dim


class EncoderService:
    def __init__(self, model_id: str, model=None):
        self.model_id = model_id
        if model is not None:
            self.model = model
        else:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(model_id)

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vectors]


class EncoderRegistry:
    def __init__(self, expected_dim: int):
        self.expected_dim = expected_dim
        self._encoders: dict[str, EncoderService] = {}
        self._dimensions: dict[str, int] = {}

    def get_encoder(self, model_id: str) -> EncoderService:
        if model_id not in self._encoders:
            self._encoders[model_id] = EncoderService(model_id)
        return self._encoders[model_id]

    def validate_embedding_dim(self, model_id: str, vectors: list[list[float]]) -> int:
        if not vectors:
            return self._dimensions.get(model_id, self.expected_dim)
        actual_dim = len(vectors[0])
        if actual_dim != self.expected_dim:
            raise EmbeddingDimensionMismatchError(
                model_id=model_id,
                expected_dim=self.expected_dim,
                actual_dim=actual_dim,
            )
        self._dimensions[model_id] = actual_dim
        return actual_dim

    def loaded_models(self) -> list[str]:
        return sorted(self._encoders.keys())

    def loaded_model_dim(self, model_id: str) -> int | None:
        return self._dimensions.get(model_id)
