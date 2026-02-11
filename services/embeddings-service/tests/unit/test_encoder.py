from app.services.encoder import EncoderService


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
