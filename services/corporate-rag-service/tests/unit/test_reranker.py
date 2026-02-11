from app.services.reranker import RerankerService


class FakeModel:
    def predict(self, pairs):
        return [0.1, 0.9]


def test_reranker_reorders_candidates():
    service = RerankerService("fake", model=FakeModel())
    candidates = [
        {"chunk_text": "first"},
        {"chunk_text": "second"},
    ]
    ranked, _ = service.rerank("query", candidates)
    assert ranked[0]["chunk_text"] == "second"
