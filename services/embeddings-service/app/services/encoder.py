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
